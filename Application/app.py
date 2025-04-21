from flask import Flask, render_template, request, jsonify, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os, shutil, base64, pickle, re, string, random, json, smtplib
import numpy as np
import cv2
from mtcnn import MTCNN
from keras_facenet import FaceNet
from email.mime.text import MIMEText
from dotenv import load_dotenv
from models import db, User, Card, CardHistory
from models import Transfer, Beneficiary


# Chargement des variables d’environnement
load_dotenv()

# Config Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=20)

# Email config
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Init DB
db.init_app(app)





@app.route('/historique')
def historique():
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()
    
    balance = getattr(user, 'balance', 3000)

    transactions = [
        {"details": "Investment", "id": "#00053", "date": "02 Jan 2025 04:56 PM", "amount": -45.00},
        {"details": "Online shopping", "id": "#00736", "date": "13 April 2024 09:33 AM", "amount": -50.02},
        {"details": "Food", "id": "#00221", "date": "25 December 2024 03:16 PM", "amount": -14.85},
    ]
    
    overdraft = 500
    return render_template("historique.html",
                            first_name=user.first_name,
                            last_name=user.last_name,
                            user_id=user.id,
                            balance=balance,
                            overdraft=overdraft,
                            transactions=transactions,
                            active_page='features')

@app.route('/signup-modal', methods=['GET', 'POST'])
def signup_modal():
    if request.method == 'GET':
        return render_template('signup_modal.html')

    data = request.form
    required_fields = ['last_name', 'first_name', 'gender', 'birthday', 'email', 'phone', 'username', 'password']
    if not all(data.get(field) for field in required_fields):
        cleanup_failed_registration()
        return jsonify({"message": "Tous les champs sont requis."}), 400

    if User.query.filter_by(email=data['email']).first():
        cleanup_failed_registration()
        return jsonify({"message": "Cet email est déjà utilisé."}), 400

    if User.query.filter_by(username=data['username']).first():
        cleanup_failed_registration()
        return jsonify({"message": "Ce nom d'utilisateur est déjà utilisé."}), 400

    if data.get('terms_accepted') != "yes":
        cleanup_failed_registration()
        return jsonify({"message": "Veuillez accepter les conditions d'utilisation."}), 400

    try:
        user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            gender=data['gender'],
            birthday=data['birthday'],
            email=data['email'],
            phone=data['phone'],
            username=data['username'],
            password=data['password'],
            biometrics="en traitement..."
        )

        db.session.add(user)
        db.session.commit()

        # 👇 Session temporaire pour l'inscription (pas encore connecté)
        session['pending_registration'] = True
        session['temp_username'] = user.username

        return jsonify({
            "message": "Inscription réussie ! Lancement du traitement biométrique...",
            "redirect": "/process-faces"
        })

    except Exception as e:
        db.session.rollback()
        print("Erreur lors de l'inscription :", str(e))
        return jsonify({"message": "Erreur serveur."}), 500


@app.route('/process-faces')
def process_faces():
    try:
        username = session.get('temp_username')
        if not username:
            return jsonify({"message": "Session expirée"}), 400

        if not session.get("pending_registration"):
            print("Tentative de traitement sans enregistrement actif.")
            return jsonify({"message": "Inscription interrompue"}), 400

        if session.get("registration_cancelled"):
            print("Traitement refusé : utilisateur a annulé l'inscription.")
            return jsonify({"message": "Inscription annulée"}), 400

        embeddings = process_faces_internal()

        if not embeddings:
            raise Exception("Aucun visage valide détecté.")

        update_embeddings(username, embeddings)

        # Nettoyage des images après succès
        folder = os.path.join('static', 'faces', 'user_temp')
        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder)

        # Nettoyage session complet après succès
        session.pop('pending_registration', None)
        session.pop('temp_username', None)
        session.pop('registration_cancelled', None)
        session.clear()

        return jsonify({"message": "Traitement terminé", "redirect": "/login-modal"})

    except Exception as e:
        print("Erreur traitement des visages:", e)

        username = session.get('temp_username')
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                db.session.delete(user)
                db.session.commit()

        cleanup_failed_registration()
        return jsonify({"message": "Erreur serveur"}), 500

    

def process_faces_internal():
    if not session.get("pending_registration") or session.get("registration_cancelled"):
        print("Traitement annulé dans process_faces_internal.")
        raise Exception("Inscription interrompue côté utilisateur.")

    folder = os.path.join('static', 'faces', 'user_temp')
    embeddings = []
    detector = MTCNN()
    embedder = FaceNet()

    for filename in os.listdir(folder):
        if filename.endswith('.png'):
            path = os.path.join(folder, filename)
            img = cv2.imread(path)
            emb = extract_embedding_from_image(img, detector, embedder)
            if emb is not None:
                embeddings.append(emb)

    return embeddings

#-------Vérifier l'état de l'enregistrement des données 
@app.route('/check-registration-status')
def check_registration_status():
    pending = session.get('pending_registration', False)
    return jsonify({"pending": pending})




# Fonction pour l'extraction des embeddings qu'on pourra utiliser aussi pour les différente reconnaissance faciale
def extract_embedding_from_image(img, detector, embedder):
    try:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = detector.detect_faces(img)
        if results and results[0]['confidence'] > 0.90:
            x, y, w, h = results[0]['box']
            x, y = max(x, 0), max(y, 0)
            face = img[y:y+h, x:x+w]
            face = cv2.resize(face, (160, 160))
            face_array = np.asarray(face)
            embedding = embedder.embeddings([face_array])[0]
            return embedding
    except Exception as e:
        print("Erreur embedding:", e)
    return None


def update_embeddings(username, new_embeddings, path='embeddings.pkl'):
    data = {}

    if os.path.exists(path):
        with open(path, 'rb') as f:
            loaded = pickle.load(f)
            if isinstance(loaded, dict):
                data = loaded
            else:
                print(" embeddings.pkl contient un format inattendu. Réinitialisation.")
    
    data[username] = new_embeddings

    with open(path, 'wb') as f:
        pickle.dump(data, f)

# Pour les conditions générales d'utilisation
@app.route('/terms')
def terms():
    if "username" not in session:
        return redirect('/')
    from_page = request.args.get("from", "")
    return render_template('terms.html', from_page=from_page)



# -------------------- ROUTES -------------------- #
@app.route('/')
def home():
    if 'username' not in session:
        return render_template('home.html')
    
    # On fait un retour sécurisé avec get

    user = User.query.filter_by(username=session['username']).first()
    valid_cards = [
        c for c in user.cards
        if not c.is_deleted and not c.is_opposed and not c.is_blocked
    ]
    main_card = sorted(valid_cards, key=lambda c: c.id)[0]
    return render_template(
        'home2.html',
        username=session.get('username'),
        first_name=session.get('first_name', ''),
        gender=session.get('gender', ''),
        user=user,
        main_card=main_card
    )    
       


@app.route('/home2')
def home2():
    if 'username' not in session:
        return redirect('/')
    
    user = User.query.filter_by(username=session['username']).first()
    valid_cards = [
        c for c in user.cards
        if not c.is_deleted and not c.is_opposed and not c.is_blocked
    ]
    main_card = sorted(valid_cards, key=lambda c: c.id)[0]
    return render_template('home2.html',user=user, main_card=main_card, username=session['username'], first_name=session['first_name'], show_auth_modals=False)

@app.route('/about')
def about():
    if 'username' not in session:
        return redirect('/')
    return render_template('about.html')




@app.route('/logout')
def logout():
    if "username" not in session:
        redirect('/')
    return render_template('home.html')

# -------------------- ENREGISTREMENT DES FACES -------------------- #
@app.route('/register-face', methods=['POST'])
def register_face():
    data = request.get_json()
    image_data = data.get('image')

    if not image_data:
        return jsonify({'message': 'Aucune image reçue'}), 400

    try:
        header, encoded = image_data.split(',', 1)
        img_bytes = base64.b64decode(encoded)
        save_dir = os.path.join('static', 'faces', 'user_temp')
        os.makedirs(save_dir, exist_ok=True)

        file_count = len(os.listdir(save_dir))
        filename = f"face_{file_count + 1:03}.png"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(img_bytes)

        return jsonify({'message': f"Image enregistrée sous {filename}"})

    except Exception as e:
        return jsonify({'message': 'Erreur serveur'}), 500

@app.route('/clear-temp-faces')
def clear_temp_faces():
    folder = os.path.join('static', 'faces', 'user_temp')
    try:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder)
        return jsonify({'message': 'Images supprimées'}), 200
    except Exception:
        return jsonify({'message': 'Erreur lors de la suppression'}), 500
    


def cleanup_failed_registration():
    folder = os.path.join('static', 'faces', 'user_temp')
    if os.path.exists(folder):
        shutil.rmtree(folder)
        os.makedirs(folder)

    username = session.get('username')
    if username and os.path.exists("embeddings.pkl"):
        with open("embeddings.pkl", "rb") as f:
            loaded = pickle.load(f)
            if isinstance(loaded, dict):
                data = loaded
                if username in data:
                    del data[username]
                    with open("embeddings.pkl", "wb") as f:
                        pickle.dump(data, f)
            else:
                print("embeddings.pkl est corrompu ou mal formé, suppression.")
                os.remove("embeddings.pkl")


    session.clear()



# -------------------- GESTION DES CARTES -------------------- #
@app.route('/add_card', methods=['GET', 'POST'])
def add_card():
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return redirect('/')

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        card_number = data.get('card_number', '').replace(" ", "").strip()
        expiration = data.get('expiration', '').strip()
        cvv = data.get('cvv', '').strip()
        holder_name = data.get('holder_name', '').strip()
        billing_address = data.get('billing_address', '').strip()
        pin = data.get('pin', '').strip()

        # Vérifications côté backend
        if not re.fullmatch(r"\d{13,19}", card_number):
            return jsonify({"status": "error", "message": "Numéro de carte invalide."}), 400

        if not re.fullmatch(r"(0[1-9]|1[0-2])/20[2-9][0-9]", expiration):
            return jsonify({"status": "error", "message": "Date d’expiration invalide (MM/YYYY)."}), 400

        if not re.fullmatch(r"\d{3,4}", cvv):
            return jsonify({"status": "error", "message": "CVV invalide."}), 400

        if not re.fullmatch(r"\d{4,6}", pin):
            return jsonify({"status": "error", "message": "PIN invalide (4 à 6 chiffres)."}), 400

        if len(billing_address) < 6:
            return jsonify({"status": "error", "message": "Adresse de facturation trop courte."}), 400

        # Vérifie si la carte existe déjà
        for card in user.cards:
            if card.card_number.replace(" ", "") == card_number:
                return jsonify({"status": "error", "message": "Cette carte existe déjà dans votre compte."}), 400

        # Limite à 3 cartes par utilisateur
        if len(user.cards) >= 3:
            return jsonify({"status": "error", "message": "Vous avez déjà atteint la limite de 3 cartes."}), 400

                # Création
        new_card = Card(
            expiration=expiration,
            holder_name=holder_name,
            billing_address=billing_address,
            user=user
        )
        new_card.card_number = card_number
        new_card.cvv = cvv
        new_card.set_pin(pin)

        db.session.add(new_card)
        db.session.commit()

        return jsonify({"status": "success", "message": "Carte ajoutée avec succès."}), 200

    return render_template('add_card.html', first_name=user.first_name, last_name=user.last_name)


@app.route('/manage_cards')
def manage_cards():
    if 'username' not in session:
        return redirect('/')

    success = request.args.get('success') == '1'
    user = User.query.filter_by(username=session['username']).first()

    first_card_id = None
    if user.cards:
        first_card_id = sorted(user.cards, key=lambda c: c.id)[0].id
        
    return render_template(
            'manage_cards.html',
            last_name=user.last_name,
            first_name=user.first_name,
            gender=user.gender,
            cards=user.cards,
            active_page='features',
            success = success,
            first_card_id=first_card_id,

    )

#-------------Opérations pour la gestion des cartes-----------------#


# Préparation de la recharge
@app.route('/prepare_recharge', methods=['POST'])
def prepare_recharge():
    data = request.get_json()
    if 'username' not in session:
        return jsonify({'status': 'unauthorized'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    target_id = int(data['target_card_id'])
    source_id = data['source_card_id']
    amount = float(data['amount'])

    # Cartes valides uniquement
    valid_cards = [
        c for c in user.cards
        if not c.is_deleted and not c.is_blocked and not c.is_opposed
    ]

    # Vérifie si la cible est une carte valide
    if not any(c.id == target_id for c in valid_cards):
        return jsonify({'status': 'error', 'message': 'Invalid target card'}), 400

    if source_id != "none" and not any(c.id == int(source_id) for c in valid_cards):
        return jsonify({'status': 'error', 'message': 'Invalid source card'}), 400

    # Nouvelle logique : recharge EXTERNE si source == target == première carte
    sorted_cards = sorted(user.cards, key=lambda c: c.id)
    is_external = (
        len(sorted_cards) >= 1 and
        str(sorted_cards[0].id) == source_id and
        str(sorted_cards[0].id) == str(target_id)
    )

    # Enregistrement en session
    session['pending_recharge'] = {
        'user_id': user.id,
        'target_card_id': target_id,
        'source_card_id': source_id,
        'amount': amount
    }

    return jsonify({ 'status': 'ok', 'external_recharge': is_external })


@app.route('/complete_recharge', methods=['POST'])
def complete_recharge():
    data = session.get('pending_recharge')
    if not data:
        return jsonify({'status': 'error', 'message': 'Session expired'}), 400

    user = User.query.get(data['user_id'])
    target_card = Card.query.get(data['target_card_id'])
    amount = data['amount']

    if not target_card or target_card.is_deleted or target_card.is_opposed:
        return jsonify({'status': 'error', 'message': 'Invalid target card'}), 400

    source_info = ""

    if 'source_card_id' in data and data['source_card_id'] != 'none':
        source_card_id = int(data['source_card_id'])
        source_card = Card.query.get(source_card_id)

        # 💡 Si c'est une recharge externe (source == target)
        if source_card.id == target_card.id:
            print(f"Recharge EXTERNE de {amount}€ sur carte {target_card.id} via vérification faciale", flush=True)
        else:
            if not source_card or source_card.balance < amount or source_card.is_blocked or source_card.is_deleted or source_card.is_opposed:
                return jsonify({'status': 'error', 'message': 'Invalid source card'}), 400

            source_card.balance -= amount
            source_info = f"from card {source_card.id}"

    # Créditer la carte cible (même si source == target, on le fait une seule fois)
    target_card.balance += amount

    print(f"Recharge de {amount}€ {source_info} to card {target_card.id}", flush=True)

    db.session.commit()
    session.pop('pending_recharge', None)

    return jsonify({'status': 'success'})


# Pour recharger la carte de rien, juste la première carte, il faut faire une reconnaissance faciale
@app.route('/verify_recharge_face', methods=['GET', 'POST'])
def verify_recharge_face():
    if request.method == 'GET':
        return render_template('verify_recharge_face.html')

    try:
        images = request.get_json().get('images', [])
    except Exception:
        return jsonify({'message': "Requête invalide."}), 400

    username = session.get('username')
    if not username or not images:
        return jsonify({'message': "Données manquantes."}), 400

    try:
        with open("embeddings.pkl", "rb") as f:
            db_embeddings = pickle.load(f)
    except Exception:
        return jsonify({'message': "Erreur chargement embeddings."}), 500

    if username not in db_embeddings:
        return jsonify({'message': "Aucune donnée biométrique pour cet utilisateur."}), 400

    stored_embedding = db_embeddings[username]
    if isinstance(stored_embedding, list) or (hasattr(stored_embedding, 'shape') and len(np.array(stored_embedding).shape) == 2):
        stored_embedding = np.mean(np.array(stored_embedding), axis=0)

    match_count = 0

    for image_data in images:
        try:
            header, encoded = image_data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            np_img = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            results = detector.detect_faces(img)
            if results:
                x, y, w, h = results[0]['box']
                x, y = max(x, 0), max(y, 0)
                face = img[y:y+h, x:x+w]
                face = cv2.resize(face, (160, 160))
                new_embedding = extract_embedding_from_image(img, detector, embedder)

                if new_embedding is not None:
                    similarity = cosine_similarity(
                        [new_embedding.flatten()],
                        [stored_embedding.flatten()]
                    )[0][0]
                    print(f"Similarité : {similarity}", flush=True)

                    if similarity > 0.65:
                        match_count += 1
        except Exception as e:
            print("Erreur image :", str(e), flush=True)

    if match_count >= 1:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'fail', 'message': "Reconnaissance échouée."}), 401


#-----POur le virement 
@app.route('/bank_transfer')
def bank_transfer():
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()

    # Sélectionne la première carte valide
    valid_cards = [
        c for c in user.cards
        if not c.is_deleted and not c.is_opposed and not c.is_blocked
    ]
    if not valid_cards:
        flash("No valid card available for transfer.")
        return redirect('/manage_cards')

    main_card = sorted(valid_cards, key=lambda c: c.id)[0]

    return render_template(
        'bank_transfer.html',
        user=user,
        main_card=main_card
    )


# Ajouter un bénéficaire
@app.route('/add_beneficiary', methods=['POST'])
def add_beneficiary():
    data = request.json
    name = data.get("name")
    iban = data.get("iban")
    card_number = data.get("card_number")

    # Vérifications simples côté serveur
    if not card_number or len(card_number) != 19 or not card_number.isdigit():
        return jsonify(success=False, error="Card number must be 16 digits.")
    if not iban or len(iban) < 10:
        return jsonify(success=False, error="Invalid IBAN.")

    user = User.query.filter_by(username=session['username']).first()

    # Création du bénéficiaire sans vérification d'existence réelle
    new_benef = Beneficiary(
        user_id=user.id,
        name=name,
        iban=iban,
        card_id=None  # Ou utiliser un champ `card_number_raw` si tu veux le stocker
    )

    db.session.add(new_benef)
    db.session.commit()

    return jsonify(success=True)


#-- Pour avoir la liste des bénéficiaires lors du virement
@app.route('/get_beneficiaries')
def get_beneficiaries():
    if 'username' not in session:
        return jsonify({"beneficiaries": []})

    user = User.query.filter_by(username=session['username']).first()

    # Récupérer les bénéficiaires liés à cet utilisateur
    beneficiaries = Beneficiary.query.filter_by(user_id=user.id).all()

    # Formater les données
    result = []
    for b in beneficiaries:
        # Récupère la carte associée au bénéficiaire
        card = Card.query.get(b.card_id)
        if not card or card.is_deleted or card.is_blocked or card.is_opposed:
            continue  # ignorer les cartes inactives

        result.append({
            "id": b.id,
            "full_name": b.name,
            "card_number_masked": card.masked_number()
        })

    return jsonify({"beneficiaries": result})

@app.route('/get_user_cards')
def get_user_cards():
    if 'username' not in session:
        return jsonify({"cards": []}), 401

    user = User.query.filter_by(username=session['username']).first()
    cards = [
        {
            "id": c.id,
            "masked": c.masked_number()
        }
        for c in user.cards
        if not c.is_deleted and not c.is_blocked and not c.is_opposed
    ]

    return jsonify({"cards": cards})


#-----Soumission du virement
# routes.py

@app.route('/submit_transfer', methods=['POST'])
def submit_transfer():
    data = request.json
    user = User.query.filter_by(username=session['username']).first()
    main_card = next(c for c in user.cards if not c.is_deleted and not c.is_blocked and not c.is_opposed)

    amount = float(data['amount'])

    if main_card.balance < amount:
        return jsonify(success=False, error="Insufficient balance")

    # Générer le code de vérification
    code = f"{random.randint(100000, 999999)}"
    session['transfer_verification_code'] = code
    session['pending_transfer'] = data

    # Envoi de mail
    send_email(
        to=user.email,
        subject="Transfer verification code",
        body=f"Your verification code is: {code}"
    )

    return jsonify(
        success=True,
        verification_required=True,
        source_card_id=main_card.id  # ✅ Cette ligne est nécessaire pour le frontend
    )

# Le virement après les vérifications
@app.route('/complete_transfer', methods=['POST'])
def complete_transfer():
    if 'pending_transfer' not in session or 'username' not in session:
        return jsonify(status='error', message='No pending transfer')

    user = User.query.filter_by(username=session['username']).first()
    transfer_data = session['pending_transfer']

    # Récupérer la carte principale de l’expéditeur
    main_card = next(c for c in user.cards if not c.is_deleted and not c.is_blocked and not c.is_opposed)

    # Vérification sécurité
    amount = float(transfer_data['amount'])
    beneficiary_id = int(transfer_data['beneficiary_id'])

    if main_card.balance < amount:
        return jsonify(status='error', message='Insufficient balance')

    # Récupérer la carte destinataire
    beneficiary = Beneficiary.query.get(beneficiary_id)
    if not beneficiary:
        return jsonify(status='error', message='Beneficiary not found')

    recipient_card = Card.query.get(beneficiary.card_id)
    if not recipient_card or recipient_card.is_blocked or recipient_card.is_deleted or recipient_card.is_opposed:
        return jsonify(status='error', message='Recipient card unavailable')

    # Effectuer le virement
    main_card.balance -= amount
    recipient_card.balance += amount

    # Enregistrer le transfert
    transfer = Transfer(
        sender_id=user.id,
        recipient_card_id=recipient_card.id,
        amount=amount,
        type=transfer_data['transfer_type'],
        motive=transfer_data['motive']
    )
    db.session.add(transfer)
    db.session.commit()

    # Nettoyer la session
    session.pop('pending_transfer', None)
    session.pop('transfer_verification_code', None)

    return jsonify(status='success', message='Transfer completed successfully')



# Bloquer temporairement la carte 
@app.route('/toggle_block/<int:card_id>', methods=['POST'])
def toggle_block(card_id):
    try:
        data = request.get_json()
        reason = data.get("reason", "")
        if not reason:
            return jsonify(status="error", message="Veuillez fournir une raison."), 400


        card = Card.query.get(card_id)
        if not card:
            return jsonify(status="error", message="Carte introuvable"), 404

        card.is_blocked = not card.is_blocked
        db.session.commit()

        # Historique
        action = "block" if card.is_blocked else "unblock"
        history = CardHistory(
            card_id=card.id,
            user_id=card.user_id,
            action=action,
            reason=reason
        )
        db.session.add(history)
        db.session.commit()

        return jsonify(
            status="success",
            message="Carte débloquée avec succès" if not card.is_blocked else "Carte bloquée avec succès",
            is_blocked=card.is_blocked
        )

    except Exception as e:
        print(f"Erreur toggle_block: {e}")
        return jsonify(status="error", message=str(e)), 500


# Faire opposition à la carte 
@app.route('/oppose_card/<int:card_id>', methods=['POST'])
def oppose_card(card_id):
    try:
        data = request.get_json()
        reason = data.get("reason", "")
        if not reason:
            return jsonify(status="error", message="Veuillez fournir une raison."), 400


        card = Card.query.get(card_id)
        if not card:
            return jsonify(status="error", message="Carte introuvable"), 404

        card.is_opposed = not card.is_opposed

        db.session.commit()

        # Historique
        action = "oppose" if card.is_opposed else "revert_oppose"
        history = CardHistory(
            card_id=card.id,
            user_id=card.user_id,
            action=action,
            reason=reason
        )
        db.session.add(history)
        db.session.commit()

        return jsonify(
            status="success",
            message="Opposition levée avec succès" if not card.is_opposed else "Carte mise en opposition",
            is_opposed=card.is_opposed
        )

    except Exception as e:
        print(f"Erreur oppose_card: {e}")
        return jsonify(status="error", message=str(e)), 500


# Consulter le code pin 
#------- Fonction d'envoie de l'email
def send_email(to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"Email envoyé à {to}")
            return True
    except Exception as e:
        print("Erreur :", e)
        return False



# Envoi du code à l'adresse mail
@app.route('/card/<int:card_id>/request_pin_code', methods=['POST'])
def request_pin_code(card_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Non autorisé"}), 403

    user = User.query.filter_by(username=session['username']).first()
    card = Card.query.filter_by(id=card_id, user_id=user.id).first()

    if not card or card.is_blocked or card.is_deleted or card.is_opposed:
        return jsonify({'error': 'Carte introuvable'}), 404


    # Génération et envoi du code
    code = ''.join(random.choices(string.digits, k=6))
    session['pin_verification_code'] = code
    success = send_email(user.email, "Code de vérification pour votre carte", f"Votre code est : {code}")

    if not success:
        return jsonify({"status": "error", "message": "Échec de l'envoi de l'email"}), 500
    
    print(f"Requête reçue pour envoyer un code à l'utilisateur {user.username} pour la carte {card.id}")
    print(f"Email : {user.email}")


    return jsonify({"status": "success", "message": "Code envoyé à votre adresse mail."})
#---- Vérification du code PIN qu'on envoie par mail à l'utilisateur (si correspond, alors on lui 
# envoie son code secret)

@app.route('/card/<int:card_id>/verify_code_and_get_pin', methods=['POST'])
def verify_code_and_get_pin(card_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Non autorisé"}), 403

    user = User.query.filter_by(username=session['username']).first()
    code_entered = request.json.get("code")
    expected = session.get('pin_verification_code')

    if code_entered != expected:
        return jsonify({"status": "error", "message": "Code incorrect"}), 403

    card = Card.query.filter_by(id=card_id, user_id=user.id).first()
    if not card:
        return jsonify({"status": "error", "message": "Carte non trouvée"}), 404

    try:
        return jsonify({"status": "success", "pin": card.get_pin()})
    except Exception:
        return jsonify({"status": "error", "message": "Erreur lors du déchiffrement du code PIN"}), 500



#-Supprimer une carte de l'application 
@app.route('/delete_card/<int:card_id>', methods=['POST'])
def delete_card(card_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Non autorisé"}), 403

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"status": "error", "message": "Utilisateur non trouvé."}), 404

    card = Card.query.filter_by(id=card_id, user_id=user.id).first()
    if not card:
        return jsonify({"status": "error", "message": "Carte introuvable"}), 404

    data = request.get_json()
    reason = data.get("reason", "")
    if not reason:
        return jsonify(status="error", message="Veuillez fournir une raison."), 400


    # Historique AVANT suppression
    history = CardHistory(
        card_id=card.id,
        user_id=card.user_id,
        action="delete",
        reason=reason
    )
    db.session.add(history)
    card.is_deleted = True
    db.session.commit()

    return jsonify({"status": "success", "message": "Carte supprimée avec succès"}), 200


#------ Garder l'historique des opérations sur les cartes cartes 
@app.route('/card_history')
def card_history():
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()
    history = CardHistory.query \
        .join(Card) \
        .filter(Card.user_id == user.id) \
        .order_by(CardHistory.timestamp.desc()) \
        .all()

    return render_template("card_history.html", user=user, history=history)

# Restoration des cartes bloquées, supprimées ou opposées
@app.route('/restore_card/<int:card_id>', methods=['POST'])
def restore_card(card_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Non autorisé"}), 403

    user = User.query.filter_by(username=session['username']).first()
    card = Card.query.filter_by(id=card_id, user_id=user.id).first()

    if not card:
        return jsonify({"status": "error", "message": "Carte introuvable"}), 404

    # Ne restaurer que si elle est marquée supprimée
    if not card.is_deleted:
        return jsonify({"status": "error", "message": "Carte non supprimée"}), 400

    data = request.get_json()
    reason = data.get("reason", "")
    if not reason:
        return jsonify(status="error", message="Veuillez fournir une raison."), 400


    card.is_deleted = False
    db.session.commit()

    # Historique
    history = CardHistory(
        card_id=card.id,
        user_id=card.user_id,
        action="restore",
        reason=reason or "Carte restaurée via historique"
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({"status": "success", "message": "Carte restaurée avec succès"}), 200
 


#------------Connexion avec reconnaissance faciale---------------#
from flask import request, jsonify, session
import os
import pickle
import numpy as np
import cv2
from mtcnn import MTCNN
from keras_facenet import FaceNet
from sklearn.metrics.pairwise import cosine_similarity

# Initialiser les outils de reconnaissance faciale
detector = MTCNN()
embedder = FaceNet()

# Pour stocker temporairement la dernière image capturée (base64 dans un vrai cas)
temp_login_image = None
@app.route('/reinitialisation_mdp', methods=['GET', 'POST'])
def reinitialisation_mdp():
    if request.method == 'POST':
        email = request.form.get('email')
        # Tu peux ici ajouter : vérification de l'email, envoi de lien, etc.
        print(f"Demande de réinitialisation pour : {email}")
        return redirect('/')
    return render_template('reinitialisation_mdp.html')

@app.route('/login-face-temp', methods=['POST', 'GET'])
def login_face_temp():
    global temp_login_image
    data = request.get_json()
    temp_login_image = data.get('image')
    return jsonify({'message': 'Image reçue'}), 200

@app.route('/login-modal', methods=['GET', 'POST'])
def login_modal():
    global temp_login_image_list

    if request.method == 'GET':
        return render_template('login_modal.html')

    # Méthode POST avec JSON
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        images = data.get('images', [])
    except Exception as e:
        return jsonify({'message': "Requête invalide."}), 400

    if not username or not password:
        return jsonify({'message': "Identifiants manquants."}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'message': "Nom d'utilisateur ou mot de passe invalide."}), 400

    if not images or len(images) == 0:
        return jsonify({'message': "Aucune image reçue pour vérification."}), 400

    # Chargement des embeddings
    try:
        with open("embeddings.pkl", "rb") as f:
            db_embeddings = pickle.load(f)
    except Exception as e:
        return jsonify({'message': "Erreur de chargement des données biométriques."}), 500

    if username not in db_embeddings:
        return jsonify({'message': "Aucune donnée biométrique enregistrée pour cet utilisateur."}), 400

    stored_embedding = db_embeddings[username]

    # Si c'est une liste (plusieurs embeddings stockés), on fait la moyenne
    if isinstance(stored_embedding, list) or isinstance(stored_embedding, np.ndarray) and len(np.array(stored_embedding).shape) == 2:
        stored_embedding = np.mean(np.array(stored_embedding), axis=0)

    match_count = 0

    for image_data in images:
        try:
            header, encoded = image_data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            np_img = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            results = detector.detect_faces(img)
            if results:
                x, y, w, h = results[0]['box']
                x, y = max(x, 0), max(y, 0)
                face = img[y:y+h, x:x+w]
                face = cv2.resize(face, (160, 160))
                new_embedding = extract_embedding_from_image(img, detector, embedder)
                if new_embedding is None:
                    continue

                stored_embedding = stored_embedding.flatten()
                new_embedding = new_embedding.flatten()
                similarity = cosine_similarity([new_embedding], [stored_embedding])[0][0]


                print("✅ Similarité:", similarity, flush=True)

                print("Forme new_embedding:", new_embedding.shape, flush=True)
                print("Forme stored_embedding:", stored_embedding.shape, flush=True)

                print("Similarité: ", similarity, flush=True)

                if similarity > 0.65:
                    match_count += 1
        except Exception as e:
            print("Erreur traitement image:", str(e), flush=True)
            continue


    if match_count >= 1:
        session['username'] = user.username
        session['first_name'] = user.first_name
        session['last_name'] = user.last_name
        session.permanent = True  # On active la session une fois que l'utilisateur se connecte
        return jsonify({'message': "Connexion réussie !", 'redirect': '/home2'})
    else:
        return jsonify({'message': "Reconnaissance faciale échouée. Veuillez réessayer."}), 401
    
#--------Faire un payement---------------#
@app.route('/make_payment', methods=['GET'])
def make_payment():
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()

    # Liste des services
    services = [
        {"id": 1, "name": "Électricité", "amount": 60.50},
        {"id": 2, "name": "Internet", "amount": 39.99},
        {"id": 3, "name": "Eau", "amount": 25.20},
    ]

    # On ne transmet que les cartes valides (non bloquées et non opposées)
    valid_cards = [card for card in user.cards if not card.is_blocked and not card.is_opposed]

    return render_template('make_payment.html',
                           user=user,
                           services=services,
                           cards=valid_cards,
                           active_page='features')

#------Vérifier les informations de paiement et mise à jour des données de l'utilisateur -------#
@app.route('/process_payment', methods=['POST'])
def process_payment():
    print("Paiement reçu")
    print("Form:", request.form)
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()

    card_id = request.form.get('card_id')
    amount = request.form.get('amount')
    cvv = request.form.get('cvv')  # récupère le CVV ici

    # Nettoyage du champ amount
    if amount:
        amount = amount.replace("€", "").replace(" ", "").strip()
    else:
        print("Champ vide")

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"message": "Montant invalide."}), 400

    # Vérifie que la carte existe
    card = Card.query.filter_by(id=card_id, user_id=user.id).first()
    if not card:
        return jsonify({"message": "Carte introuvable ou non autorisée."}), 403

    # Vérifie le CVV
    if not cvv or cvv != card.cvv:
        return jsonify({"message": "Code CVV incorrect."}), 403

    # Vérifie les statuts
    if card.is_blocked or card.is_opposed:
        return jsonify({"message": "Carte bloquée ou en opposition."}), 403

    # Vérifie le solde
    if card.balance < amount:
        return jsonify({"message": "Solde insuffisant pour effectuer ce paiement."}), 400

    #Si tout est ok soustraire et enregistrer
    card.balance -= amount
    db.session.commit()
    return jsonify({
        "message": "Paiement réussi !",
        "redirect": f"/payment_success?amount={amount}&card_id={card.id}"
    })



@app.route('/payment_success')
def payment_success():
    if 'username' not in session:
        return redirect('/')

    amount = request.args.get("amount")
    card_id = request.args.get("card_id")

    user = User.query.filter_by(username=session["username"]).first()
    card = Card.query.filter_by(id=card_id, user_id=user.id).first()

    if not card:
        return redirect('/')

    return render_template("payment_success.html", amount=amount, card=card)

#---------------Supprimer les enregistrements---------------#
@app.route('/cancel-registration')
def cancel_registration():
    try:
        folder = os.path.join('static', 'faces', 'user_temp')
        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder)

        # Utilise temp_username car l'utilisateur n'est pas encore connecté
        username = session.get('temp_username')
        if username and os.path.exists("embeddings.pkl"):
            with open("embeddings.pkl", "rb") as f:
                data = pickle.load(f)
            if username in data:
                del data[username]
                with open("embeddings.pkl", "wb") as f:
                    pickle.dump(data, f)

        # Supprimer le user de la DB si présent
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()

        # Marque l’annulation (le flag sera lu plus tard dans process_faces)
        session['registration_cancelled'] = True

        return jsonify({"message": "Annulation réussie"}), 200

    except Exception as e:
        print("Erreur annulation :", e)
        return jsonify({"message": "Erreur serveur"}), 500


# -------------------- MAIN -------------------- #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

""""""

# -------------------- PROCESS FACES -------------------- #

# -------------------- OUTILS -------------------- #


""""""
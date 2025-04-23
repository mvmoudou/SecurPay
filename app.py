from flask import Flask, render_template, request, jsonify, session, redirect
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
    print("/process-faces appelé")
    print("session[username]:", session.get("temp_username"))

    try:
        username = session.get('temp_username')
        print("Utilisateur temporaire :", username)

        if not username:
            return jsonify({"message": "Session expirée"}), 400

        if not session.get("pending_registration"):
            print("Tentative de traitement sans enregistrement actif.")
            return jsonify({"message": "Inscription interrompue"}), 400

        if session.get("registration_cancelled"):
            print("Traitement refusé : utilisateur a annulé l'inscription.")
            return jsonify({"message": "Inscription annulée"}), 400

        print("Avant traitement biométrique")
        embeddings = process_faces_internal()
        print("Embeddings générés :", embeddings)
        print("Avant traitement biométrique")


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

    

import gc  # À ajouter tout en haut de ton fichier si pas encore fait

detector = MTCNN()
embedder = FaceNet()
def process_faces_internal():
    if not session.get("pending_registration") or session.get("registration_cancelled"):
        print("Traitement annulé dans process_faces_internal.")
        raise Exception("Inscription interrompue côté utilisateur.")

    folder = os.path.join('static', 'faces', 'user_temp')
    embeddings = []


    print(f"Lecture des images dans : {folder}")
    files = [f for f in os.listdir(folder) if f.endswith('.png')]
    print(f"{len(files)} images trouvées.")

    for filename in files:
        path = os.path.join(folder, filename)
        img = cv2.imread(path)
        emb = extract_embedding_from_image(img, detector, embedder)

        if emb is not None:
            embeddings.append(emb)
            print(f" Visage détecté dans {filename} — total valides : {len(embeddings)}")

        # Libération de mémoire
        del img
        del emb
        gc.collect()

        if len(embeddings) >= 10:
            print("Limite de 10 visages atteinte, arrêt anticipé.")
            break

    print(f"Total d'embeddings retenus : {len(embeddings)}")
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
    from_page = request.args.get("from", "")
    return render_template('terms.html', from_page=from_page)



# -------------------- ROUTES -------------------- #
@app.route('/')
def home():
    if 'username' not in session:
        return render_template('home.html')
    
    # On fait un retour sécurisé avec get
    return render_template(
        'home2.html',
        username=session.get('username'),
        first_name=session.get('first_name', ''),
        gender=session.get('gender', '')
    )    
       


@app.route('/home2')
def home2():
    if 'username' not in session:
        return redirect('/')
    return render_template('home2.html', username=session['username'], first_name=session['first_name'], show_auth_modals=False)

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
    print("==> Route /add_card appelée")
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

@app.route('/debug_session')
def debug_session():
    return jsonify(dict(session))


@app.route('/manage_cards')
def manage_cards():
    try:
        if 'username' not in session:
            print("Pas de session active")
            return redirect('/')

        user = User.query.filter_by(username=session['username']).first()
        if not user:
            print("Utilisateur introuvable :", session['username'])
            return redirect('/')

        print("Utilisateur trouvé :", user.username)

        return render_template(
            'manage_cards.html',
            last_name=user.last_name,
            first_name=user.first_name,
            gender=user.gender,
            cards=user.cards,
            active_page='features'
        )
    except Exception as e:
        print("ERREUR manage_cards :", str(e))
        return f"Erreur serveur : {str(e)}", 500

#-------------Opérations pour la gestion des cartes-----------------#

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
    except Exception as e:
        print("Erreur :", e)


# Envoi du code à l'adresse mail
@app.route('/card/<int:card_id>/request_pin_code', methods=['POST'])
def request_pin_code(card_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Non autorisé"}), 403

    user = User.query.filter_by(username=session['username']).first()
    card = Card.query.filter_by(id=card_id, user_id=user.id).first()

    if not card:
        return jsonify({"status": "error", "message": "Carte introuvable"}), 404

    # Génération et envoi du code
    code = ''.join(random.choices(string.digits, k=6))
    session['pin_verification_code'] = code
    send_email(user.email, "Code de vérification pour votre carte", f"Votre code est : {code}")

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


""""""

# -------------------- PROCESS FACES -------------------- #

# -------------------- OUTILS -------------------- #


""""""
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
import os, shutil, base64, pickle
import numpy as np
import cv2
import json
from mtcnn import MTCNN
from keras_facenet import FaceNet
from datetime import timedelta # Pour étendre la session de la session de l'utilisateur une fois qu'il 
from models import db, User, Card


app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=20)

db.init_app(app)




@app.route('/historique')
def historique():
    if 'username' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['username']).first()
    
    # Exemple de récupération du solde depuis ta base (si tu l'as)
    # Ici on suppose un champ user.balance ou alors tu le calcules
    balance = getattr(user, 'balance', 3000)

    transactions = [
        {"details": "Investment", "id": "#00053", "date": "02 Jan 2025 04:56 PM", "amount": "-45.00"},
        {"details": "Online shopping", "id": "#00736", "date": "13 April 2024 09:33 AM", "amount": "-50.02"},
        {"details": "Food", "id": "#00221", "date": "25 December 2024 03:16 PM", "amount": "-14.85"},
    ]
    overdraft = 500  # Exemple fixe
    return render_template("historique.html",
                            first_name=user.first_name,
                            last_name=user.last_name,
                            user_id=user.id,
                            balance=balance,
                            overdraft=overdraft,
                            transactions=transactions)

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
        # Dans signup_modal, modifiez la création de l'utilisateur :
        user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            gender=data['gender'],
            birthday=data['birthday'],
            email=data['email'],
            phone=data['phone'],
            username=data['username'],
            password=generate_password_hash(data['password']),  # Hasher le mot de passe
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


@app.route('/settings')
def settings():
    if 'username' not in session:
        return redirect('/login-modal')
    return render_template('settings.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"message": "Ce compte n'existe pas. Veuillez vous inscrire."}), 404

    if not check_password_hash(user.password, password):
        return jsonify({"message": "Mot de passe incorrect. Cliquez sur 'mot de passe oublié' pour réinitialiser."}), 401

    # Connexion réussie → on enregistre l’utilisateur en session
    session['username'] = user.username
    session['first_name'] = user.first_name
    session['last_name'] = user.last_name
    session['gender'] = user.gender

    return jsonify({
        "message": "Connexion réussie !",
        "redirect": "/home2"
    }), 200




@app.route('/logout')
def logout():
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



        # ✅ Sinon, création du compte
        user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            gender = data['gender'],
            birthday=data['birthday'],
            email=data['email'],
            phone=data['phone'],
            username=data['username'],
            password=generate_password_hash(data['password']),
            biometrics="SampleData"
        )

        with open(file_path, 'wb') as f:
            f.write(img_bytes)


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
        card_number = request.form['card_number']
        expiration = request.form['expiration']
        cvv = request.form['cvv']
        holder_name = request.form['holder_name']
        billing_address = request.form['billing_address']
        pin = request.form['pin']  #  nouveau champ

        # Création de la carte
        new_card = Card(
            card_number=card_number,
            expiration=expiration,
            cvv=cvv,
            holder_name=holder_name,
            billing_address=billing_address,
            user=user
        )
        new_card.set_pin(pin)  #  chiffrer et stocker le code PIN

        db.session.add(new_card)
        db.session.commit()

        print("Carte ajoutée :", new_card.masked_number())
        return redirect('/manage_cards?success=1')

    return render_template('add_card.html', first_name=session['first_name'], last_name=session['last_name'])

@app.route('/manage_cards')
def manage_cards():
    if 'username' not in session:
        return redirect('/')

    success = request.args.get('success') == '1'
    user = User.query.filter_by(username=session['username']).first()
    return render_template(
            'manage_cards.html',
            last_name=user.last_name,
            first_name=user.first_name,
            gender=user.gender,
            cards=user.cards
    )

#-------------Opérations pour la gestion des cartes-----------------#

# Bloquer temporairement la carte 
@app.route('/toggle_block/<int:card_id>', methods=['POST'])
def toggle_block(card_id):
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify(status="error", message="Card not found"), 404
        card.is_blocked = not card.is_blocked
        db.session.commit()
        return jsonify(status="success", is_blocked=card.is_blocked)
    except Exception as e:
        print(f"Erreur toggle_block: {e}")
        return jsonify(status="error", message=str(e)), 500

# Faire opposition à la carte 
@app.route('/oppose_card/<int:card_id>', methods=['POST'])
def oppose_card(card_id):
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify(status="error", message="Card not found"), 404
        card.is_opposed = not card.is_opposed
        db.session.commit()
        return jsonify(status="success", is_opposed=card.is_opposed)
    except Exception as e:
        print(f"Erreur oppose_card: {e}")
        return jsonify(status="error", message=str(e)), 500

# Consulter le code pin 
@app.route('/card/<int:card_id>/get_pin')
def get_pin(card_id):
    card = Card.query.get(card_id)
    if card:
        try:
            return jsonify(pin=card.get_pin())
        except Exception as e:
            return jsonify(error="Erreur lors du déchiffrement du code PIN")
    return jsonify(error="Carte non trouvée")


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

                if similarity > 0.6:
                    match_count += 1
        except Exception as e:
            print("Erreur traitement image:", str(e), flush=True)
            continue


    if match_count >= 3:
        session['username'] = user.username
        session['first_name'] = user.first_name
        session['last_name'] = user.last_name
        session.permanent = True  # On active la session une fois que l'utilisateur se connecte
        return jsonify({'message': "Connexion réussie !", 'redirect': '/home2'})
    else:
        return jsonify({'message': "Reconnaissance faciale échouée. Veuillez réessayer."}), 401


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
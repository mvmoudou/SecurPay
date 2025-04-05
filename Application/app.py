from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
import os, shutil, base64, pickle
import numpy as np
import cv2
from mtcnn import MTCNN
from keras_facenet import FaceNet

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    gender = db.Column(db.String(1))
    birthday = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    biometrics = db.Column(db.Text)

@app.route('/signup-modal', methods=['GET', 'POST'])
def signup_modal():
    if request.method == 'GET':
        return render_template('signup_modal.html')

    # Méthode POST (soumission du formulaire)
    data = request.form

    required_fields = ['last_name', 'first_name', 'gender', 'birthday', 'email', 'phone', 'username', 'password']
    if not all(data.get(field) for field in required_fields):
        cleanup_failed_registration()
        return jsonify({"message": "Tous les champs sont requis."}), 400

    # Vérification unicité email et username
    if User.query.filter_by(email=data['email']).first():
        cleanup_failed_registration()
        return jsonify({"message": "Cet email est déjà utilisé."}), 400

    if User.query.filter_by(username=data['username']).first():
        cleanup_failed_registration()
        return jsonify({"message": "Ce nom d'utilisateur est déjà utilisé."}), 400

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

        session['username'] = user.username
        session['first_name'] = user.first_name
        session['last_name'] = user.last_name
        session['gender'] = user.gender

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
        username = session.get('username')
        if not username:
            return jsonify({"message": "Session expirée"}), 400

        embeddings = process_faces_internal()

        if not embeddings:
            raise Exception("Aucun visage valide détecté.")

        update_embeddings(username, embeddings)

        # ✅ Ne supprime pas user_temp ici
        return jsonify({"message": "Traitement terminé", "redirect": "/home2"})

    except Exception as e:
        print("Erreur traitement des visages:", e)

        username = session.get('username')
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                db.session.delete(user)
                db.session.commit()

        # ✅ Nettoyage complet seulement en cas d’échec
        cleanup_failed_registration()

        return jsonify({"message": "Erreur serveur"}), 500


def process_faces_internal():
    folder = os.path.join('static', 'faces', 'user_temp')
    embeddings = []
    detector = MTCNN()
    embedder = FaceNet()

    for filename in os.listdir(folder):
        if filename.endswith('.png'):
            path = os.path.join(folder, filename)
            img = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
            results = detector.detect_faces(img)
            if results and results[0]['confidence'] > 0.90:
                x, y, w, h = results[0]['box']
                x, y = max(x, 0), max(y, 0)
                face = img[y:y+h, x:x+w]
                face_resized = cv2.resize(face, (160, 160))
                face_array = np.asarray(face_resized)

                # ✅ CORRECT ici : on accède directement à l’indice [0]
                embedding = embedder.embeddings([face_array])[0]
                embeddings.append(embedding)

    return embeddings

def update_embeddings(username, new_embeddings, path='embeddings.pkl'):
    data = {}

    if os.path.exists(path):
        with open(path, 'rb') as f:
            loaded = pickle.load(f)
            if isinstance(loaded, dict):
                data = loaded
            else:
                print("⚠️ embeddings.pkl contient un format inattendu. Réinitialisation.")
    
    data[username] = new_embeddings

    with open(path, 'wb') as f:
        pickle.dump(data, f)


class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expiration = db.Column(db.String(7))
    cvv = db.Column(db.String(4))
    holder_name = db.Column(db.String(100))
    billing_address = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship('User', backref=db.backref('cards', lazy=True))

# -------------------- ROUTES -------------------- #
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/home2')
def home2():
    if 'username' not in session:
        return redirect('/')
    return render_template('home2.html', username=session['username'], first_name=session['first_name'])

@app.route('/about')
def about():
    return render_template('about.html')



@app.route('/logout')
def logout():
    return render_template('home.html')

from flask import make_response, request, render_template, json

@app.route('/signup-modal', methods=['GET', 'POST'])
def signup_modal():
    if request.method == 'POST':
        data = request.form

        # ❌ Si email déjà utilisé
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"message": "Cet email est déjà utilisé."}), 400

        # ❌ Si username déjà utilisé
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"message": "Ce nom d'utilisateur est déjà utilisé."}), 400

        # ✅ Sinon, création du compte
        user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            gender = data['gender'],
            birthday=data['birthday'],
            email=data['email'],
            phone=data['phone'],
            username=data['username'],
            password=data['password'],
            biometrics="SampleData"
        )

        try:
            db.session.add(user)
            db.session.commit()
            session['username'] = user.username
            session['first_name'] = user.first_name
            session['last_name'] = user.last_name
            session['gender'] = user.gender

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

    if request.method == 'POST':
        expiration = request.form['expiration']
        cvv = request.form['cvv']
        holder_name = request.form['holder_name']
        billing_address = request.form['billing_address']

        print("Carte ajoutée :", expiration, cvv, holder_name, billing_address)
        return redirect('/manage_cards')

    return render_template('add_card.html', first_name=session['first_name'], last_name=session['last_name'])

@app.route('/manage_cards')
def manage_cards():
    if 'username' not in session:
        return redirect('/')

    return render_template(
        'manage_cards.html',
        last_name=session.get('last_name', ''),
        first_name=session.get('first_name', ''),
        gender=session.get('gender', '')
    )


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

@app.route('/login-face-temp', methods=['POST', 'GET'])
def login_face_temp():
    global temp_login_image
    data = request.get_json()
    temp_login_image = data.get('image')
    return jsonify({'message': 'Image reçue'}), 200


@app.route('/login-modal', methods=['POST'])
def login_modal():
    global temp_login_image_list

    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'message': "Nom d'utilisateur ou mot de passe invalide."}), 400

    # Récupérer les images en base64
    images = request.json.get('images', [])
    if not images or len(images) == 0:
        return jsonify({'message': "Aucune image reçue pour vérification."}), 400

    # Charger les embeddings
    with open("embeddings.pkl", "rb") as f:
        db_embeddings = pickle.load(f)

    if username not in db_embeddings:
        return jsonify({'message': "Aucune donnée biométrique enregistrée pour cet utilisateur."}), 400

    stored_embedding = db_embeddings[username]
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
                new_embedding = embedder.embeddings([face])[0]
                similarity = cosine_similarity([new_embedding], [stored_embedding])[0][0]

                if similarity > 0.7:
                    match_count += 1
        except Exception as e:
            continue  # On ignore les erreurs pour les images ratées

    if match_count >= 6:
        session['username'] = user.username
        session['first_name'] = user.first_name
        session['last_name'] = user.last_name
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

        # Supprimer l'entrée dans embeddings.pkl
        username = session.get('username')
        if username and os.path.exists("embeddings.pkl"):
            with open("embeddings.pkl", "rb") as f:
                data = pickle.load(f)

            if username in data:
                del data[username]
                with open("embeddings.pkl", "wb") as f:
                    pickle.dump(data, f)

        # On peut aussi supprimer le user de la DB si voulu :
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()

        # Nettoyer session
        session.clear()

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
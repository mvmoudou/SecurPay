# SecurPay – Application de Paiement Sécurisée

SecurPay est une application de paiement avec **authentification multifactorielle**, combinant mot de passe et reconnaissance faciale. Elle permet de **gérer ses cartes bancaires (physiques et virtuelles)**, d’effectuer des paiements, de bloquer ou faire opposition à une carte, et de consulter l’historique des actions.

## Fonctionnalités principales

- **Inscription & Connexion avec reconnaissance faciale** (via webcam)
- **Ajout de cartes bancaires** (3 maximum par utilisateur)
- **Masquage des numéros**, cryptage des données sensibles (PIN, CVV)
- **Blocage temporaire**, **opposition** ou **suppression** d’une carte avec raison
- **Vérification par email** pour consulter le code PIN
- **Historique des actions** (restaurer une carte, lever opposition…)
- **Paiement avec confirmation** et sélection de service/carte
- Interface intuitive et responsive (Le but en tout cas)

## Technologies utilisées

- **Backend** : Flask, SQLAlchemy, SQLite
- **Frontend** : HTML5, CSS3, JavaScript (modales dynamiques, effet popup)
- **Sécurité** : 
  - Authentification biométrique avec `cv2` + `MTCNN`
  - Chiffrement Fernet (`cryptography`)
  - Email sécurisé via SMTP Gmail
- **Reconnaissance faciale** : `keras-facenet`, `TensorFlow`, `MTCNN`
- **Stockage** : Base SQLite avec historique via modèle `CardHistory`

## Authentification biométrique

- Capture automatique de visages via webcam
- Enregistrement d’un vecteur facial (embedding)
- Vérification par similarité lors de la connexion

## Installation


```bash

1. Clonez le dépôt :
git clone https://github.com/Moudou3/SecurPay.git
cd SecurPay

2. Creer un environnement virtuel et activer le
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

3. Installer les dépendances
pip install -r requirements.txt

4. Créez un fichier .env à la racine avec les variables suivantes 
EMAIL_ADDRESS=ton.email@gmail.com
EMAIL_PASSWORD=mot_de_passe_application
SECRET_KEY=clé_ultra_secrète

Pense à activer l’option « mot de passe d’application » si tu utilises un compte Gmail avec la vérification en 2 étapes.

5. Initialiser la base de données
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()

6. Lancer l'application
flask run

7. Ouvre ton navigateur sur
http://127.0.0.1:5000/

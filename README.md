# SecurPay

SecurPay est une application web de paiement bancaire développée avec **Flask**, intégrant une authentification classique (identifiant/mot de passe) ainsi qu'une **reconnaissance faciale** pour sécuriser la connexion et la gestion des cartes bancaires (blocage, opposition, suppression, historique).

## Fonctionnalités

- **Inscription / Connexion** classiques avec hachage des mots de passe (`werkzeug.security`)
- **Reconnaissance faciale** (détection via `MTCNN` + embeddings via `FaceNet`) pour l'enregistrement et la vérification d'identité
- **Gestion des cartes bancaires** : ajout, blocage/déblocage, opposition, suppression, restauration
- **Chiffrement des données sensibles** (numéro de carte, CVV, code PIN) avec `cryptography.Fernet`
- **Historique des cartes** et des transactions
- **Réinitialisation de mot de passe** par email (SMTP)
- **Paiement en ligne** avec page de succès

## Stack technique

| Domaine | Technologies |
|---|---|
| Backend | Flask, Flask-SQLAlchemy, Flask-Login |
| Base de données | SQLite |
| Sécurité | cryptography (Fernet), werkzeug (hash de mots de passe) |
| Reconnaissance faciale | TensorFlow, Keras-FaceNet, MTCNN, OpenCV, scikit-learn |
| Frontend | HTML, CSS, JavaScript (templates Jinja2) |
| Déploiement | Gunicorn (voir `Procfile`) |

## Prérequis

- Python 3.10 (recommandé — des fichiers `.pyc` compilés en 3.10 et 3.7 sont présents dans le repo)
- pip

## Installation

1. **Cloner le projet**
   ```bash
   git clone <url-du-repo>
   cd SecurPay-main
   ```

2. **Créer un environnement virtuel**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows : venv\Scripts\activate
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d'environnement**

   Créer un fichier `.env` à la racine du projet avec :
   ```env
   FERNET_KEY=votre_cle_fernet
   EMAIL_ADDRESS=votre_email@gmail.com
   EMAIL_PASSWORD=votre_mot_de_passe_application
   ```

   Pour générer une clé Fernet valide :
   ```bash
   python generate_key.py
   ```

   > ⚠️ Le `.env` est ignoré par Git (`.gitignore`) : ne jamais commiter vos secrets.

5. **Initialiser la base de données**
   ```bash
   python init_db.py
   ```

## Lancer l'application

En développement :
```bash
python app.py
```

En production (via Gunicorn, comme défini dans le `Procfile`) :
```bash
gunicorn app:app
```

L'application est accessible par défaut sur `http://127.0.0.1:5000`.

## Structure du projet

```
SecurPay-main/
├── app.py                  # Routes et logique principale Flask
├── models.py                # Modèles SQLAlchemy (User, Card, CardHistory)
├── init_db.py                # Script d'initialisation de la base de données
├── generate_key.py           # Génération d'une clé de chiffrement Fernet
├── requirements.txt           # Dépendances Python
├── Procfile                  # Commande de démarrage pour le déploiement
├── static/
│   ├── css/                  # Feuilles de style par page
│   ├── js/                   # Scripts JS par page
│   ├── images/                # Ressources graphiques
│   └── models/                # Modèles de détection faciale (tiny_face_detector)
└── templates/                 # Templates HTML (Jinja2)
```

## Principales routes

| Route | Description |
|---|---|
| `/` | Page d'accueil |
| `/signup-modal` | Inscription |
| `/login-modal` | Connexion |
| `/register-face` | Enregistrement biométrique du visage |
| `/process-faces` | Traitement des images capturées |
| `/manage_cards` | Gestion des cartes bancaires |
| `/add_card` | Ajout d'une carte |
| `/toggle_block/<id>` | Blocage / déblocage d'une carte |
| `/oppose_card/<id>` | Mise en opposition d'une carte |
| `/delete_card/<id>` | Suppression d'une carte |
| `/card_history` | Historique des actions sur les cartes |
| `/make_payment` | Formulaire de paiement |
| `/process_payment` | Traitement du paiement |
| `/reinitialisation_mdp` | Réinitialisation du mot de passe |

## Sécurité

- Les numéros de carte, CVV et codes PIN sont **chiffrés en base** via Fernet (AES symétrique).
- Les mots de passe utilisateurs sont **hachés**.
- Les données faciales temporaires (`static/faces/user_temp/`) et les fichiers sensibles (`.env`, `users.db`, `embeddings.pkl`) sont exclus du versioning.

## Avertissement

Ce projet est un prototype à but pédagogique/démonstratif. Certaines pratiques (clé secrète Flask générée aléatoirement à chaque démarrage, données de transactions simulées, etc.) ne sont pas adaptées à un environnement de production réel sans révision approfondie de la sécurité.

## Auteurs

- SIDIBE Mamoudou
- ROSALIE Corine
- WIAM 
- LÉNO CELESTINE

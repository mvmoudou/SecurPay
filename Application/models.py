import os
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Charger les variables d’environnement
load_dotenv()

# Initialisation
db = SQLAlchemy()

# Clé de chiffrement Fernet à stocker dans .env
FERNET_KEY = os.getenv('FERNET_KEY')
if not FERNET_KEY:
    raise ValueError("La clé FERNET_KEY n’est pas définie dans l’environnement")
fernet = Fernet(FERNET_KEY.encode())


# --- Modèle Utilisateur ---
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

    # Relation avec les cartes
    cards = db.relationship('Card', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


# --- Modèle Carte Bancaire avec chiffrement du numéro ---
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    _card_number = db.Column("card_number", db.LargeBinary, nullable=False)  # Champ chiffré
    expiration = db.Column(db.String(7), nullable=False)
    cvv = db.Column(db.String(4), nullable=False)
    holder_name = db.Column(db.String(100), nullable=False)
    billing_address = db.Column(db.String(200), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def card_number(self):
        try:
            return fernet.decrypt(self._card_number).decode()
        except Exception:
            return "[Erreur de déchiffrement]"

    @card_number.setter
    def card_number(self, plain_number):
        self._card_number = fernet.encrypt(plain_number.encode())

    def masked_number(self):
        """Retourne le numéro de carte masqué, ex : **** **** **** 1234"""
        number = self.card_number
        return "**** **** **** " + number[-4:] if number else "Numéro non dispo"

    def __repr__(self):
        return f"<Card {self.masked_number()} pour {self.user.username}>"

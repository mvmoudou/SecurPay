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


# --- Modèle Carte Bancaire avec chiffrement du numéro et du CVV ---
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    _card_number = db.Column("card_number", db.LargeBinary, nullable=False)  # Champ chiffré
    expiration = db.Column(db.String(7), nullable=False)
    _cvv = db.Column("cvv", db.LargeBinary, nullable=False)  # Champ chiffré
    holder_name = db.Column(db.String(100), nullable=False)
    billing_address = db.Column(db.String(200), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)
    is_opposed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pin_encrypted = db.Column(db.LargeBinary, nullable=False)
    balance = db.Column(db.Float, default=100.0) # Le montant par défaut 


    @property
    def card_number(self):
        try:
            return fernet.decrypt(self._card_number).decode()
        except Exception:
            return "[Erreur de déchiffrement]"

    @card_number.setter
    def card_number(self, plain_number):
        self._card_number = fernet.encrypt(plain_number.encode())

    @property
    def cvv(self):
        try:
            return fernet.decrypt(self._cvv).decode()
        except Exception:
            return "[Erreur de déchiffrement]"

    @cvv.setter
    def cvv(self, plain_cvv):
        self._cvv = fernet.encrypt(plain_cvv.encode())

    def masked_number(self):
        number = self.card_number
        return "**** **** **** " + number[-4:] if number else "Numéro non dispo"

    def __repr__(self):
        return f"<Card {self.masked_number()} pour {self.user.username}>"

    def set_pin(self, pin_plaintext):
        self.pin_encrypted = fernet.encrypt(pin_plaintext.encode())

    def get_pin(self):
        return fernet.decrypt(self.pin_encrypted).decode()

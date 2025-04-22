from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(key.decode())  # à copier et stocker de façon sécurisée (ex: dans un fichier .env)

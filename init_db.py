from app import app, db  # importe ton app Flask et l'objet db
# assure-toi que app et db sont bien importables ici !

with app.app_context():
    print("Suppression des anciennes tables...")
    db.drop_all()
    print("Suppression terminée. Création des nouvelles tables...")
    db.create_all()
    print("Base de données initialisée avec succès.")

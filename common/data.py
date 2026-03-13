import database

#!!!!!!!!!!!!!!!!!!!!
DB_PATH = "database.db"
#!!!!!!!!!!!!!!!!!!!!

def user_exists(name: str) -> bool:
    """
    Détermine l'existence d'un utilisateur sur base de son nom (pseudonyme)
    :param name: le nom de l'utilisateur (pseudonyme)
    :return: `True` si un utilisateur existe sur base du nom fourni, sinon `False`
    """
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    database.close_connection(connexion)
    if not resultat:
        return False
    else:
        return True
#
# Remplacez ce commentaire par vos propres fonctions d'accès et de modification de données
#

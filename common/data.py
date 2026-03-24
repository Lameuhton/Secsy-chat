from common import database
from nanoid import generate
from datetime import datetime

#!!!!!!!!!!!!!!!!!!!!
DB_PATH = "database.db"
#!!!!!!!!!!!!!!!!!!!!

def user_exists(name: str) -> bool:
    """
    Détermine l'existence d'un utilisateur sur base de son nom (pseudonyme)
    :param name: le nom de l'utilisateur (pseudonyme)
    :return: `True` si un utilisateur existe sur base du nom fourni, sinon `False`
    """
    connexion = database.connect_to_db(DB_PATH) # Indique au passage à la fonction qu'on utilise sqlite3 grâce à database
    cursor = connexion.cursor()
    cursor.execute("SELECT * FROM user WHERE name = ?", (name,)) # Il y a une virgule après name pourqu'il soit considéré comme un tuple (exécute utilise un tuple)
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    database.close_connection(connexion)
    if not resultat:
        return False
    else:
        return True

def create_user(name: str, hashed_password):
    '''
    Crée un tilisateur avec le pseudo et le mot de passe précédemment hashé et l'encode dans la base de donnée.
    :param name: le nom de l'utilisateur (pseudonyme)
    :param hashed_password: mot de passe précédemment hashé
    '''

    id = generate()
    now = datetime.now()
    connexion = database.connect_to_db(DB_PATH)
    database.insert_data(connexion,"user", ("id", "name", "secret", "created_at", "last_activity_at"), (id, name, hashed_password, now, now))
    database.close_connection(connexion)


def get_user(name: str) -> Tuple[str, str, str, str, str]:
    """
    Récupère les informations d'un utilisateur existant à partir de son pseudonyme.

    Cette fonction suppose que l'utilisateur existe déjà dans la base de données.
    La vérification d'existence doit être effectuée au préalable avec la fonction
    `user_exists`.

    :param name: le nom (pseudonyme) de l'utilisateur à récupérer
    :return: un tuple contenant les informations de l'utilisateur.

             Structure du tuple retourné :
             (
                id,
                name,
                secret,             #mot de passe hashé
                created_at,
                last_activity_at
             )
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT * FROM user WHERE name = ?", (name,))
    resultat = cursor.fetchall()
    database.close_connection(connexion)
    
    # [0] car fetchall retourne une liste de tuples (qui normalement chez nous n'en contient qu'un mais pour s'adapter au format de fetchall on doit mettre le 0)
    return resultat[0]
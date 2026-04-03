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
    cursor.execute("SELECT 1 FROM user WHERE name = ?", (name,)) # Il y a une virgule après name pourqu'il soit considéré comme un tuple (exécute utilise un tuple)
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


def get_user(name: str) -> tuple:
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
    resultat = cursor.fetchone()

    # Eviter des erreurs ou crashs si jamais ca ne retourne rien
    if resultat is None:
        return None

    return resultat
    
def update_user_last_activity(user_id: str):
    """
    Met à jour le champ `last_activity_at` d’un utilisateur en base de données
    avec le timestamp actuel.

    Cette fonction est appelée lorsqu’un utilisateur effectue une action
    (ex : envoi de message), afin de garder une trace de sa dernière activité.

    :param user_id: identifiant unique de l'utilisateur à mettre à jour
    """

    now = datetime.now()
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("UPDATE user SET last_activity_at = ? WHERE id = ?", (now, user_id))
    connexion.commit()
    database.close_connection(connexion)


def add_message(message: dict):
    """
    Cette fonction prend en entrée un dictionnaire représentant un message déjà
    validé (issu du parsing du JSON reçu). Elle extrait les informations
    nécessaires et les insère dans la table `channel_message`.
    :param message: dictionnaire contenant les informations du message (format du return de parse_message)
    """

    message_id = generate()
    message_timestamp = message["timestamp"]
    message_sender_id = message["sender"]["id"]
    message_recipient_id = message["recipient"]["id"]
    message_payload_cipher_text = message["payload"]["cipher_text"]
    message_payload_cipher_text_size = message["payload"]["cipher_text_size"]
    message_payload_cipher_text_encrypted_key = message["payload"]["cipher_text_encrypted_key"]
    message_integrity_checksum = message["integrity"]["checksum"]
    message_integrity_signature = message["integrity"]["signature"]
    
    connexion = database.connect_to_db(DB_PATH)
    
    database.insert_data(
        connexion,
        "channel_message",
        (
            "id",
            "timestamp",
            "sender_id",
            "recipient_id",
            "payload_cipher_text",
            "payload_cipher_text_size",
            "payload_cipher_text_encrypted_key",
            "integrity_checksum",
            "integrity_signature"
        ),
        (
            message_id,
            message_timestamp,
            message_sender_id,
            message_recipient_id,
            message_payload_cipher_text,
            message_payload_cipher_text_size,
            message_payload_cipher_text_encrypted_key,
            message_integrity_checksum,
            message_integrity_signature
        )
    )
    
    database.close_connection(connexion)
    
    
    
    
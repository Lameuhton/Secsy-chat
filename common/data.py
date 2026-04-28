from typing import List, Tuple

from common import database, security
from nanoid import generate
from datetime import datetime

#!!!!!!!!!!!!!!!!!!!!
DB_PATH = "database.db"
#!!!!!!!!!!!!!!!!!!!!


# ---------- User ------------

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

def create_user(name: str, hashed_password, public_key: str):
    '''
    Crée un tilisateur avec le pseudo et le mot de passe précédemment hashé et l'encode dans la base de donnée.
    :param name: le nom de l'utilisateur (pseudonyme)
    :param hashed_password: mot de passe précédemment hashé
    :param public_key: clé publique de l'utilisateur
    '''

    id = generate()
    now = datetime.now()
    connexion = database.connect_to_db(DB_PATH)
    database.insert_data(connexion,"user", ("id", "name", "secret", "public_key", "created_at", "last_activity_at"), (id, name, hashed_password, public_key, now, now))
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
                public_key,
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
    
    database.close_connection(connexion)

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


# ---------- Channel Message ------------

def get_last_channel_message(channel_id: str) -> List[Tuple]:
    """
    Récupère les derniers messages d'un channel à partir de son identifiant unique.
     :param channel_id: l'identifiant unique du channel
     :return: une liste de tuples contenant les informations des messages du channel.

             Structure des tuples retournés :
             (
                id,
                timestamp,
                sender_id,
                recipient_id,
                payload_cipher_text,
                payload_cipher_text_size,
                payload_cipher_text_encrypted_key,
                integrity_checksum,
                integrity_signature
             )
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor() # Crée un curseur (analogie du bibliothécaire)
    cursor.execute("SELECT * FROM channel_message WHERE recipient_id = ? ORDER BY timestamp DESC LIMIT 20", (channel_id,))
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    database.close_connection(connexion)
    return resultat

def add_channel_message(message: dict):
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


#---------- Channel ------------

def add_channel(channel: dict, owner_id):
    """
    Cette fonction prend en entrée un dictionnaire représentant un channel déjà
    validé (issu du parsing du JSON reçu). Elle extrait les informations
    nécessaires et les insère dans la table `channel`.
    :param channel: dictionnaire contenant les informations du channel (format du return des fonctions parse dans statement)
    :owner_id: str - id du user qui a crée le channel   
    """

    channel_id = generate()
    channel_name = channel["payload"]["data"]["name"]
    channel_secret = channel["payload"]["data"]["secret"]
    private_key, public_key = security.rsa_generate_keypair()
    channel_private_key = private_key.hex()
    channel_public_key = public_key.hex()
    channel_created_at = channel["timestamp"]
    channel_owner_id = owner_id 
    
    connexion = database.connect_to_db(DB_PATH)
    
    database.insert_data(
        connexion,
        "channel",
        ( # Noms des champs en BD
            "id",
            "name",
            "secret",
            "private_key",
            "public_key",
            "created_at",
            "owner_id"
        ),
        (  # Noms des variables données dans la fonction de base qui devront être insérées dans les noms des champs en BD
            channel_id,
            channel_name,
            channel_secret,
            channel_private_key,
            channel_public_key,
            channel_created_at,
            channel_owner_id
        )
    )
    
    database.close_connection(connexion)


# ---------- Messages privés (plus tard) ------------

def get_last_private_message(user_id: str) -> List[Tuple]:

    # A changer plus tard

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor() # Crée un curseur (analogie du bibliothécaire)
    # Message "safe" des injections car ? sera remplacé par du txt considéré comme python
    # Il y a "OR" car on prend autant les messages envoyés par Michel que ceux qu'il a reçus
    cursor.execute("SELECT * FROM private_message WHERE  sender_id = ? OR recipient_id = ? ORDER BY timestamp DESC  LIMIT 20", (user_id, user_id))
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    database.close_connection(connexion)
    return resultat


def add_private_message(message: dict):
    """
    Cette fonction prend en entrée un dictionnaire représentant un message déjà
    validé (issu du parsing du JSON reçu). Elle extrait les informations
    nécessaires et les insère dans la table `private_message`.
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
        "private_message",
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



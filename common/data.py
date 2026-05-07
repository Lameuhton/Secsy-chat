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
    :return: l'id de l'utilisateur créé
    '''

    id = generate()
    now = datetime.now()
    connexion = database.connect_to_db(DB_PATH)
    database.insert_data(connexion,"user", ("id", "name", "secret", "public_key", "created_at", "last_activity_at"), (id, name, hashed_password, public_key, now, now))
    database.close_connection(connexion)
    return id


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
    
    database.close_connection(connexion)

    # Eviter des erreurs ou crashs si jamais ca ne retourne rien
    if resultat is None:
        return None

    return resultat

def get_username(user_id: str) -> str:
    """
    Récupère le pseudonyme d'un utilisateur à partir de son identifiant unique.

    :param user_id: l'identifiant unique de l'utilisateur
    :return: le pseudonyme de l'utilisateur, ou `None` si inexistant
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT name FROM user WHERE id = ?", (user_id,))
    resultat = cursor.fetchone()
    
    database.close_connection(connexion)

    if resultat is None:
        return None
    
    # résultat est un tuple du style ("pseudo",) donc on prend le premier élément du tuple pour retourner juste le pseudo
    return resultat[0] 

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

def get_last_channel_message(channel_id: str, limit: int = 20) -> List[Tuple]:
    """
    Récupère les derniers messages d'un channel à partir de son identifiant unique.
    
    :param channel_id: l'identifiant unique du channel
    :param limit: le nombre maximum de messages à récupérer
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
                integrity_signature,
                recipient_type (CHANNEL dans ce cas-ci)
             )
    """

    connexion = database.connect_to_db(DB_PATH)
    resultat = database.select_data(connexion, "SELECT * FROM channel_message WHERE recipient_id = ? ORDER BY timestamp DESC LIMIT ?", (channel_id, limit))
    # Rajoute à chaque tuple un champ supplémentaire qui indique que c'est un message channel (CHANNEL)
    resultat = [tuple(list(row) + ["CHANNEL"]) for row in resultat]
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

def add_channel(channel: dict, owner_id) -> Tuple[str, str, str]:
    """
    Cette fonction prend en entrée un dictionnaire représentant un channel déjà
    validé (issu du parsing du JSON reçu). Elle extrait les informations
    nécessaires et les insère dans la table `channel`.
    
    :param channel: dictionnaire contenant les informations du channel (format du return des fonctions parse dans statement)
    :param owner_id: str - id du user qui a crée le channel
    :return: un tuple contenant l'id du channel créé, sa clé privée et sa clé publique
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
    return (channel_id, channel_private_key, channel_public_key)

#------------------- A FAIRE ------------------------
def channel_exists(name: str) -> bool:
    """
    Détermine l'existence d'un channel sur base de son nom.

    :param name: nom du channel
    :return: True si le channel existe, sinon False
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()

    cursor.execute("SELECT 1 FROM channel WHERE name = ?",(name,))

    resultat = cursor.fetchall()

    database.close_connection(connexion)

    return bool(resultat)

def get_channel_name(channel_id: str) -> str:
    """
    Récupère le nom d'un channel à partir de son identifiant unique.

    :param channel_id: l'identifiant unique du channel
    :return: le nom du channel, ou `None` si inexistant
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT name FROM channel WHERE id = ?", (channel_id,))
    resultat = cursor.fetchone()
    
    database.close_connection(connexion)

    if resultat is None:
        return None
    
    # résultat est un tuple du style ("channel_name",) donc on prend le premier élément du tuple pour retourner juste le nom du channel
    return resultat[0]

def user_exists_in_channel(user_id: str, channel_id: str) -> bool:
    """
    Détermine l'existence d'un utilisateur dans un channel sur base de son id
    
    :param user_id: l'id de l'utilisateur
    :param channel_id: l'id du channel
    :return: `True` si un utilisateur existe sur base du nom fourni, sinon `False`
    """
    connexion = database.connect_to_db(DB_PATH) 
    cursor = connexion.cursor()
    cursor.execute("SELECT 1 FROM channel_member WHERE user_id = ? AND channel_id = ?", (user_id, channel_id)) 
    # Rappel : Il y a une virgule après la requête SQL pourqu'il soit considéré comme un tuple (exécute utilise un tuple)
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    database.close_connection(connexion)
    if not resultat:
        return False
    else:
        return True

def verify_channel_secret(channel_id: str, secret: str) -> bool:
    """
    Vérifie si le secret fourni correspond au secret du channel.

    :param channel_id: id du channel
    :param secret: secret fourni par l'utilisateur
    :return: True si le secret est correct, sinon False
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT secret FROM channel WHERE id = ?", (channel_id,))
    resultat = cursor.fetchone()
    database.close_connection(connexion)

    # Channel inexistant
    if resultat is None:
        return False

    channel_secret = resultat[0]

    # Vérification du secret
    return channel_secret == secret

def add_user_to_channel(user_id: str, channel_id: str) -> None:
    """
    Ajoute un utilisateur à un canal.
    Doit insérer une entrée dans la table `channel_member` avec la date d'ajout.
    Contraintes : Vérifier que l'utilisateur existe et que le canal existe | Éviter les doublons (vérfier si le user déjà membre)
    
    :param user_id: Identifiant de l'utilisateur à ajouter
    :param channel_id: Identifiant du canal
    :return: None
    """
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()

    # Vérification de l'existence de l'utilisateur
    cursor.execute("SELECT 1 FROM user WHERE id = ?", (user_id,))
    if not cursor.fetchall():
        database.close_connection(connexion)
        return None

    # Vérification de l'existence du canal
    cursor.execute("SELECT 1 FROM channel WHERE id = ?", (channel_id,))
    if not cursor.fetchall():
        database.close_connection(connexion)
        return None

    # Vérification si l'utilisateur est déjà membre du canal (pour éviter les doublons)
    if user_exists_in_channel(user_id, channel_id) :
        database.close_connection(connexion)
        return None
    # Sinon, on ajoute l'utilisateur au canal
    else :
        now = datetime.now()
        database.insert_data(connexion,"channel_member", ("channel_id", "user_id", "joined_at"), (channel_id, user_id, now))
        database.close_connection(connexion)
        return None

def remove_user_from_channel(user_id: str, channel_id: str) -> None:
    """
    Supprime un utilisateur d'un canal.
    Doit supprimer l'entrée correspondante dans `channel_member`.
    Contraintes : Vérifier que l'utilisateur est bien membre
    
    :param user_id: Identifiant de l'utilisateur
    :param channel_id: Identifiant du canal
    :return: None
    """
    if user_exists_in_channel(user_id, channel_id) :
        connexion = database.connect_to_db(DB_PATH)
        cursor = connexion.cursor()
        cursor.execute("DELETE FROM channel_member WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
        connexion.commit()
        database.close_connection(connexion)
        return None
    else :
          return None

def get_user_channels(user_id: str) -> List[dict]:
    """
    Récupère tous les canaux dont un utilisateur est membre dans la base de données --> jointure entre `channel_member` et `channel`
    :param user_id: Identifiant de l'utilisateur
    :return: Liste des canaux (dict)
    Exemple de retour :
    [
        {"id": "...", "name": "..."},
        ...
    ]
    """
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    # Dans cette requête : On croise les deux tables pour récupérer les infos du canal pour chaque entrée 
    # dans channel_member qui correspond à l'utilisateur.
    cursor.execute("SELECT channel.* FROM channel JOIN channel_member ON channel.id = channel_member.channel_id WHERE channel_member.user_id = ?", (user_id,))
    liste_channel = cursor.fetchall()
    # Retourne une liste de tuples (un par canal), pas juste un seul résultat.
    database.close_connection(connexion)
    if liste_channel:
        # Rappel - channel = (id, name, secret, private_key, public_key, created_at, owner_id)
        return [{"id": row[0], "name": row[1], "public_key": row[4]} for row in liste_channel]
    else :    
        return None
    
def get_channel_members(channel_id: str) -> List[dict]:
    """
    Récupère tous les membres d'un canal dans la base de données --> une jointure entre `channel_member` et `user`
    :param channel_id: Identifiant du canal
    :return: Liste des utilisateurs (dict)
    """
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT user.* FROM user JOIN channel_member ON user.id = channel_member.user_id WHERE channel_member.channel_id = ?", (channel_id,))
    liste_members = cursor.fetchall()
    database.close_connection(connexion)
    if liste_members:
        # # Rappel = user = (id, name, secret, public_key, created_at, last_activity_at)
        return [{"id": row[0], "name": row[1], "public_key": row[3]} for row in liste_members]
    else :    
        return None
    
def delete_channel(channel_id: str) -> None:
    """
    Supprime un canal.

    :param channel_id: Identifiant du canal
    :return: None

    Doit :
    - Supprimer le canal dans `channel`
    - Supprimer automatiquement ses membres (CASCADE recommandé)

    Note :
    Si ON DELETE CASCADE est bien configuré sur channel_member,
    Rappel = contrainte définie directement dans la base de données (dans database.py, dans le CREATE TABLE channel_member)
    SQLite supprimera automatiquement les membres du canal.
    Sinon, ajouter manuellement :
    cursor.execute("DELETE FROM channel_member WHERE channel_id = ?", (channel_id,))
    """
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("DELETE FROM channel WHERE id = ?", (channel_id,))
    connexion.commit()
    database.close_connection(connexion)
    return None
    
def get_channel_owner(channel_id: str) -> str:
    """
    Vérifie si un utilisateur est le propriétaire d'un canal.

    :param channel_id: Identifiant du canal
    :param user_id: Identifiant de l'utilisateur
    :return: True si l'utilisateur est le propriétaire, False sinon

     Doit vérifier que le champ `owner_id` du canal correspond à l'id de l'utilisateur.

    Utile pour :
    - Vérifier les droits (kick, delete, etc.)
    """
    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor()
    cursor.execute("SELECT owner_id FROM channel WHERE id = ?", (channel_id,))
    channel_owner = cursor.fetchone() # Ici, on attend un seul résultat
    database.close_connection(connexion)
    if channel_owner:
        return channel_owner[0] # [0] car fetchone() retourne un tuple — on veut juste le owner_id
    else :
        return None

# ---------- Messages privés (plus tard) ------------

def get_last_private_message(user_id: str) -> List[Tuple]:
    """
    Récupère les derniers messages privés d'un utilisateur à partir de son identifiant unique.
    
    :param user_id: l'identifiant unique de l'utilisateur
    :return: une liste de tuples contenant les informations des messages privés de l'utilisateur.
                
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
            integrity_signature,
            recipient_type (USER dans ce cas-ci)
        )
    """

    connexion = database.connect_to_db(DB_PATH)
    cursor = connexion.cursor() # Crée un curseur (analogie du bibliothécaire)
    # Message "safe" des injections car ? sera remplacé par du txt considéré comme python
    # Il y a "OR" car on prend autant les messages envoyés par Michel que ceux qu'il a reçus
    cursor.execute("SELECT * FROM private_message WHERE  sender_id = ? OR recipient_id = ? ORDER BY timestamp DESC  LIMIT 20", (user_id, user_id))
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    # Rajoute à chaque tuple un champ supplémentaire qui indique que c'est un message privé (USER)
    resultat = [tuple(list(row) + ["USER"]) for row in resultat]
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



#
# Créez des dictionnaires ou des data classes pour structurer l'évènement
#

import json
import time

def parse_event(payload: bytes):
    """
    Lit et transforme la charge en évènement
    :param payload la charge (payload) en bytes
    :return l'évènement sous forme d'un dictionnaire ou d'un objet
    """

    # Décodage bytes → Parsing JSON → dictionnaire Python
    data = json.loads(payload.decode("utf-8"))

    # Extraction des informations importantes

    timestamp = data.get("timestamp")
    payload = data.get("payload", {})
    payload_name = payload.get("name") # type: ignore

    payload_data = payload.get("data", {}) # type: ignore
    
    if payload_name in ("CHANNEL_CREATED", "CHANNEL_JOINED"):
        parsed_data = parse_channel_created_joined(payload_data)

    elif payload_name == "CHANNEL_DELETED":
        parsed_data = parse_channel_deleted(payload_data)

    elif payload_name == "USER_UPDATED":
        parsed_data = parse_user_updated(payload_data)


    return {
        "timestamp": timestamp,
        "payload": {
            "name": payload_name,
            "data": parsed_data
        }
    }
  
def parse_channel_created_joined(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "public_key": data.get("public_key"),
        "private_key": data.get("private_key")
    }

def parse_channel_deleted(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "member_id": data.get("member_id"),
        "member_name": data.get("member_name")
    }

def parse_user_updated(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "public_key": data.get("public_key"),
        "status": data.get("status")
    }

def build_user_updated(timestamp: float, user_id: str, name: str, status: bool, public_key: bytes) -> dict:
    """
    Construit un événement USER_UPDATED standardisé.
    
    :param timestamp: timestamp de l'événement
    :param user_id: identifiant du user
    :param name: pseudo du user
    :param status: True (connecté) / False (déconnecté)
    :param public_key: clé publique du user
    :return: dictionnaire de l'événement
    """
    
    return {
        "timestamp": timestamp,
        "payload": {
            "name": "USER_UPDATED",
            "data": {
                "id": user_id,
                "name": name,
                "public_key": public_key.decode('utf-8'),
                "status": status
            }
        }
    }

def build_channel_created(timestamp: float, channel_id: str, channel_name: str, public_key: bytes, private_key: bytes = None) -> dict:
    """
    Construit un événement CHANNEL_CREATED standardisé.
    
    :param timestamp: timestamp de l'événement
    :param channel_id: identifiant du channel créé
    :param channel_name: nom du channel créé
    :param public_key: clé publique du channel créé
    :param private_key: clé privée du channel créé (optionnelle)
    :return: dictionnaire de l'événement
    """
    data = {
        "id": channel_id,
        "name": channel_name,
        "public_key": public_key.decode('utf-8')
    }

    if private_key is not None:
        data["private_key"] = private_key.decode('utf-8')

    return {
        "timestamp": timestamp,
        "payload": {
            "name": "CHANNEL_CREATED",
            "data": data
        }
    }

def build_channel_joined(timestamp: float, channel_id: str, channel_name: str, public_key: bytes, private_key: bytes = None) -> dict:
    """
    Construit un événement CHANNEL_JOINED standardisé.
    
    :param timestamp: timestamp de l'événement
    :param channel_id: identifiant du channel rejoint
    :param channel_name: nom du channel rejoint
    :param public_key: clé publique du channel rejoint
    :param private_key: clé privée du channel rejoint (optionnelle)
    :return: dictionnaire de l'événement
    """
    data = {
        "id": channel_id,
        "name": channel_name,
        "public_key": public_key.decode('utf-8')
    }

    if private_key is not None:
        data["private_key"] = private_key.decode('utf-8')   
    
    return {
        "timestamp": timestamp,
        "payload": {
            "name": "CHANNEL_JOINED",
            "data": data
        }
    }

def build_channel_deleted(timestamp: float, channel_id: str, channel_name: str, member_id: str = None, member_name: str = None) -> dict:
    """
    Construit un événement CHANNEL_DELETED standardisé.
    
    :param timestamp: timestamp de l'événement
    :param channel_id: identifiant du channel supprimé
    :param channel_name: nom du channel supprimé
    :param member_id: identifiant du membre qui a supprimé le channel (optionnel)
    :param member_name: nom du membre qui a supprimé le channel (optionnel)
    :return: dictionnaire de l'événement
    """
    data = {
        "id": channel_id,
        "name": channel_name
    }
    
    if member_id is not None:
        data["member_id"] = member_id
    if member_name is not None:
        data["member_name"] = member_name
        
    return {
        "timestamp": timestamp,
        "payload": {
            "name": "CHANNEL_DELETED",
            "data": data
        }
    }
# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également

# --> Fonction de parsing : fonction de parsing est une fonction qui analyse et interprète une chaîne de caractères 
# (ou un flux de données) pour en extraire une structure ou des informations
# Exemple - Parsing de données structurées (JSON) (Import JSON)

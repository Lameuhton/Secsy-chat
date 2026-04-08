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
    payload_name = payload.get("name")

    payload_data = payload.get("data", {})
    
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

def build_user_updated(timestamp: float, user_id: str, name: str, status: bool) -> dict:
    """
    Construit un événement USER_UPDATED standardisé.
    
    :param timestamp: timestamp de l'événement
    :param user_id: identifiant du user
    :param name: pseudo du user
    :param status: True (connecté) / False (déconnecté)
    :return: dictionnaire de l'événement
    """
    
    return {
        "timestamp": timestamp,
        "payload": {
            "name": "USER_UPDATED",
            "data": {
                "id": user_id,
                "name": name,
                "public_key": "",
                "status": status
            }
        }
    }

# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également

# --> Fonction de parsing : fonction de parsing est une fonction qui analyse et interprète une chaîne de caractères 
# (ou un flux de données) pour en extraire une structure ou des informations
# Exemple - Parsing de données structurées (JSON) (Import JSON)

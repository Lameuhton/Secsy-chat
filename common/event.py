#
# Créez des dictionnaires ou des data classes pour structurer l'évènement
#

import json

def parse_event(payload: bytes):
    """
    Lit et transforme la charge en évènement
    :param payload la charge (payload) en bytes
    :return l'évènement sous forme d'un dictionnaire ou d'un objet
    """

    # Décodage bytes → string
    json_str = payload.decode('utf-8')

    # Parsing JSON → dictionnaire Python
    data = json.loads(json_str)

    # Extraction des informations importantes

    timestamp = data.get("timestamp")
    payload = data.get("payload", {})
    payload_name = payload.get("name")

    payload_data = payload.get("data", {})
    
    match payload_name:

        case "CHANNEL_CREATED":
            parsed_data = parse_channel_created(payload_data)

        case "CHANNEL_JOINED":
            parsed_data = parse_channel_joined(payload_data)

        case "CHANNEL_DELETED":
            parsed_data = parse_channel_deleted(payload_data)

        case "USER_UPDATED":
            parsed_data = parse_user_updated(payload_data)

        case _:
            parsed_data = payload_data  # fallback safe

    return {
        "timestamp": timestamp,
        "payload": {
            "name": payload_name,
            "data": parsed_data
        }
    }
  
def parse_channel_created(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "public_key": data.get("public_key"),
        "private_key": data.get("private_key")
    }
    
def parse_channel_joined(data: dict) -> dict:
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

# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également

# --> Fonction de parsing : fonction de parsing est une fonction qui analyse et interprète une chaîne de caractères 
# (ou un flux de données) pour en extraire une structure ou des informations
# Exemple - Parsing de données structurées (JSON) (Import JSON)

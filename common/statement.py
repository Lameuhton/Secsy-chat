#
# Créez des dictionnaires ou des data classes pour structurer l'instruction
#

import json

def parse_statement(payload: bytes):
    """
    Lit et transforme la charge en instruction
    :param payload la charge (payload) en bytes
    :return l'instruction sous forme d'un dictionnaire ou d'un objet
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

        case "CREATE_CHANNEL":
            parsed_data = parse_create_channel(payload_data)

        case "DELETE_CHANNEL":
            parsed_data = parse_delete_channel(payload_data)

        case "GET_LAST_MESSAGES":
            parsed_data = parse_get_last_messages(payload_data)

        case "JOIN_CHANNEL":
            parsed_data = parse_join_channel(payload_data)

        case "KICK_CHANNEL_MEMBER":
            parsed_data = parse_kick_channel_member(payload_data)
        
        case "LEAVE_CHANNEL":
            parsed_data = parse_leave_channel(payload_data)
            
        case "UPDATE_USER":
            parsed_data = parse_update_user(payload_data)
    
        case _:
            parsed_data = payload_data  # fallback safe

    return {
        "timestamp": timestamp,
        "payload": {
            "name": payload_name,
            "data": parsed_data
        }
    }

def parse_create_channel(data: dict) -> dict:
    return {
        "name": data.get("name"),
        "secret": data.get("secret"),
    }
    
def parse_delete_channel(data: dict) -> dict:
    return {
        "name": data.get("name")
    }

def parse_get_last_messages(data: dict) -> dict:
    return {
        "channel_name": data.get("channel_name"),
        "number": data.get("number")
    }

def parse_join_channel(data: dict) -> dict:
    return {
        "name": data.get("name"),
        "secret": data.get("secret")
    }

def parse_kick_channel_member(data: dict) -> dict:
    return {
        "channel_name": data.get("channel_name"),
        "member_name": data.get("member_name")
    }
    
def parse_leave_channel(data: dict) -> dict:
    return {
        "name": data.get("channel_name")
    }
    
def parse_update_user(data: dict) -> dict:
    return {
        "status": data.get("status"),
    }
#
# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également
#

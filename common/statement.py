#
# Créez des dictionnaires ou des data classes pour structurer l'instruction
#

import json
import time
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
    parsed = {
        "name": data.get("name")
    }

    if data.get("secret") is not None:
        parsed["secret"] = data.get("secret")
        
    return parsed

def parse_kick_channel_member(data: dict) -> dict:
    return {
        "channel_name": data.get("channel_name"),
        "member_name": data.get("member_name")
    }
    
def parse_leave_channel(data: dict) -> dict:
    return {
        "name": data.get("name")
    }
    
def parse_update_user(data: dict) -> dict:
    return {
        "status": data.get("status"),
    }

def build_update_user(status: bool) -> dict:
    """
    Construit une instruction UPDATE_USER standardisée.
    
    :param status: True (connecté) / False (déconnecté)
    :return: dictionnaire de l'instruction
    """

    return {
        "timestamp": time.time(),
        "payload": {
            "name": "UPDATE_USER",
            "data": {
                "status": status
            }
        }
    }

def build_get_users() -> dict:
    """
    Construit une instruction GET_USERS standardisée.
    
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "GET_USERS"
        }
    }

def build_get_channels() -> dict:
    """
    Construit une instruction GET_CHANNELS standardisée.
    
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "GET_CHANNELS"
        }
    }
    
def build_get_last_messages(channel_name: str, number: int) -> dict:
    """
    Construit une instruction GET_LAST_MESSAGES standardisée.
    
    :param channel_name: nom du canal
    :param number: nombre de messages à récupérer
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "GET_LAST_MESSAGES",
            "data": {
                "channel_name": channel_name,
                "number": number
            }
        }
    }

def build_create_channel(name: str, secret: str) -> dict:
    """
    Construit une instruction CREATE_CHANNEL standardisée.
    
    :param name: nom du canal à créer
    :param secret: mot de passe du canal
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "CREATE_CHANNEL",
            "data": {
                "name": name,
                "secret": secret
            }
        }
    }

def build_delete_channel(name: str) -> dict:
    """
    Construit une instruction DELETE_CHANNEL standardisée.
    
    :param name: nom du canal à supprimer
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "DELETE_CHANNEL",
            "data": {
                "name": name
            }
        }
    }

def build_join_channel(name: str, secret: str = None) -> dict:
    """
    Construit une instruction JOIN_CHANNEL standardisée.
    
    :param name: nom du canal à rejoindre
    :param secret: mot de passe du canal (optionnel)
    :return: dictionnaire de l'instruction
    """
    data = {
        "name": name
    }
    
    if secret is not None:
        data["secret"] = secret
        
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "JOIN_CHANNEL",
            "data": data
        }
    }

def build_kick_channel_member(channel_name: str, member_name: str) -> dict:
    """
    Construit une instruction KICK_CHANNEL_MEMBER standardisée.
    
    :param channel_name: nom du canal
    :param member_name: nom du membre à expulser
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "KICK_CHANNEL_MEMBER",
            "data": {
                "channel_name": channel_name,
                "member_name": member_name
            }
        }
    }

def build_leave_channel(name: str) -> dict:
    """
    Construit une instruction LEAVE_CHANNEL standardisée.
    
    :param name: nom du canal à quitter
    :return: dictionnaire de l'instruction
    """
 
    return {
        "timestamp": time.time(),
        "payload": {
            "name": "LEAVE_CHANNEL",
            "data": {
                "name": name
            }
        }
    }
#
# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également
#

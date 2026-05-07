#
# Créez des dictionnaires ou des data classes pour structurer le message
#

import json

def parse_message(payload: bytes):
    """
    Lit et transforme la charge en message
    :param payload la charge (payload) en bytes
    :return le message sous forme d'un dictionnaire ou d'un objet
    """

    # Décodage bytes → string
    json_str = payload.decode('utf-8')

    # Parsing JSON → dictionnaire Python
    data = json.loads(json_str)

    # Extraction des informations importantes

    timestamp = data.get("timestamp")
    sender = data.get("sender", {})
    sender_name = sender.get("name")
    sender_id = sender.get("id")
    recipient = data.get("recipient", {})
    recipient_type = recipient.get("type")
    payload_data = data.get("payload", {})
    payload_cipher_text = payload_data.get("cipher_text")
    recipient_id = recipient.get("id")
    recipient_name = recipient.get("name")
    payload_cipher_text_size = payload_data.get("cipher_text_size")
    payload_cipher_text_encrypted_key = payload_data.get("cipher_text_encrypted_key")

    # Décommenter plus tard pour itération suivante

    # integrity = data.get("integrity", {})
    # integrity_checksum = integrity.get("checksum")
    # integrity_signature = integrity.get("signature")

    return {
        "timestamp": timestamp,
        "sender": {
            "id": sender_id,
            "name": sender_name
            },
        "recipient": {
            "type": recipient_type,
            "id": recipient_id,
            "name": recipient_name
            },
        "payload": {
            "cipher_text": payload_cipher_text,
            "cipher_text_size": payload_cipher_text_size,
            "cipher_text_encrypted_key": payload_cipher_text_encrypted_key
            },
        "integrity": {
            "checksum": "",
            "signature": ""
        }
    }
    
def build_message(data: dict, sender_name: str, recipient_name: str, recipient_type: str) -> dict:
    """
    Construit un message à partir d'un dictionnaire
    
    :param data: un dictionnaire contenant les informations nécessaires à la construction du message
    :param sender_name: le nom de l'expéditeur
    :param recipient_name: le nom du destinataire
    :param recipient_type: le type du destinataire (user ou channel)
    :return le message sous forme d'un dictionnaire ou d'un objet    
    """
    return {
        "timestamp": data[1],
        "sender": {
            "id": data[2],
            "name": sender_name
            },
        "recipient": {
            "type": recipient_type,
            "id": data[3],
            "name": recipient_name
            },
        "payload": {
            "cipher_text": data[4],
            "cipher_text_size": data[5],
            "cipher_text_encrypted_key": data[6]
            },
        "integrity": {
            "checksum": data[7],
            "signature": data[8]
        }
    }

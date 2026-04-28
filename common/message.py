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
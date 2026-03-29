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

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Par encore traités pour cette itération car par encore de notion de cannaux et d'intégrité
    # (mais à uncomment et à rajouter dans le return plus tard )

    # payload_data = payload.get("data", {})
    # payload_data_name = payload_data.get("name")
    # payload_data_secret = payload_data.get("secret")
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    return {
        "timestamp": timestamp,
        "payload": {
            "name": payload_name,
            "data": {
                "name": "X",
                "secret": "XXXXXXXXXXXXXXXXXXXXX"
                }
            }
        }

#
# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également
#

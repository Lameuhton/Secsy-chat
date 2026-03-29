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

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Par encore traités pour cette itération car par encore de notion de cannaux et d'intégrité
    # (mais à uncomment et à rajouter dans le return plus tard )

    # payload_data = payload.get("data", {})
    # payload_data_id = payload_data.get("id")
    # payload_data_name = payload_data.get("name")
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    return {
        "timestamp": timestamp,
        "payload": {
            "name": payload_name,
            "data": {
                "id": "xxxxxxxxxxxxxxxxxxxxx",
                "name": "X"
                }
            }
        }
    

# Ajoutez vos dictionnaires/data classes pour structurer les différents "data" possibles
# Ajoutez vos fonctions de parsing également

# --> Fonction de parsing : fonction de parsing est une fonction qui analyse et interprète une chaîne de caractères 
# (ou un flux de données) pour en extraire une structure ou des informations
# Exemple - Parsing de données structurées (JSON) (Import JSON)

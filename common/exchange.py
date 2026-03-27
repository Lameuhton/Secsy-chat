from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Enum = liste de constantes nommées
# Ça permet d’éviter d’utiliser des "1", "2", "3" un peu partout dans le code sans savoir à quoi ça correspond (message, statement ou event)
# → c’est plus lisible et moins source d’erreurs

class ExchangeType(Enum):
    MESSAGE = 1         # 1 = message classique envoyé par un client
    STATEMENT = 2       # 2 = instruction (commande client → serveur)
    EVENT = 3           # 3 = événement (serveur → clients)   


# Rappel structure d'un échange:
#   [0:10]   → header (taille)
#   [10:11]  → type
#   [11:]    → charge/payload (données utiles, ex: message chiffré, instruction, événement, etc.)

def get_type(exchange: bytes) -> ExchangeType:
    """
    Récupère le type d'échange depuis l'en-tête (header) de l'échange
    :param exchange l'échange en bytes
    :return le type de l'échange
    """

    try:
        # On récupère le 11e byte (index 10 car on commence à 0)
        # IMPORTANT : on prend [10:11] et PAS [10]
        # → [10:11] retourne des bytes (ex: b'1')
        # → [10] retournerait un int (ex: 49), ce qu’on ne veut pas ici
        type_byte = exchange[10:11]
        
        # On transforme les bytes en string ("1")
        type_str = type_byte.decode()

        # Puis en entier (1)
        type_int = int(type_str)

        # On convertit cet entier en Enum (1 devient ExchangeType.MESSAGE, etc.)
        return ExchangeType(type_int)
    
    except Exception as e:
        logger.error(f"Erreur get_type: {e}", exc_info=True)
        return None

def get_payload(exchange: bytes) -> bytes:
    """
    Récupère la charge (payload) de l'échange
    :param exchange l'échange en bytes
    :return la charge en bytes
    """

    try:
        # La charge commence à partir du 11e byte (index 10)
        payload = exchange[11:]
        return payload
    
    except Exception as e:
        logger.error(f"Erreur get_payload: {e}", exc_info=True)
        return None
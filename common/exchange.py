from enum import Enum


class ExchangeType(Enum):
    MESSAGE = 1
    STATEMENT = 2
    EVENT = 3


def get_type(exchange: bytes) -> ExchangeType:
    """
    Récupère le type d'échange depuis l'en-tête (header) de l'échange
    :param exchange l'échange en bytes
    :return le type de l'échange
    """


def get_payload(exchange: bytes) -> bytes:
    """
    Récupère la charge (payload) de l'échange
    :param exchange l'échange en bytes
    :return la charge en bytes
    """

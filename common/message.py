#
# Créez des dictionnaires ou des data classes pour structurer le message
#


def parse_message(payload: bytes):
    """
    Lit et transforme la charge en message
    :param payload la charge (payload) en bytes
    :return le message sous forme d'un dictionnaire ou d'un objet
    """

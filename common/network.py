import socket
import time


def start_tcp_server(ip: str, port: int) -> socket.socket:
    """
    Démarre un socket TCP qui écoute en mode "serveur" sur une IPv4 et un port précis
    :param ip l'adresse IPv4 sur laquelle écouter
    :param port le port sur lequel écouter
    :return le socket "server" créé
    """
    # Crée un objet sock qui a comme config de base IPV4 (AF_INET) et TCP (SOCK_STREAM)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # On attache le socket à une adresse IP et un port précis sur la machine ("écoute sur cette interface, sur ce port")
    sock.bind((ip, port))
    # Passe le socket en mode écoute. Prêt à recevoir des connexions entrantes, mais il ne les accepte pas encore
    sock.listen()
    return sock

def connect_tcp_server(ip: str, port: int, retry=60) -> socket.socket:
    """
    Crée un socket TCP qui tente de se connecter à un serveur en utilisant une IPv4 et un port précis.
    En cas d'échec, une nouvelle tentative de connexion a lieu après <retry> secondes
    :param ip l'adresse IPv4 à utiliser pour se connecter
    :param port le port à utiliser pour se connecter
    :param retry le nombre de seconde à attendre avant de tenter une nouvelle connexion
    :return: le socket "client" créé
    """
    # While True car il faut que la boucle se répète jusqu'à ce qu'il y ait connexion
    while True:
        # Crée à nouveau (pour éviter des interférences) un objet sock qui a comme config de base IPV4 (AF_INET) et TCP (SOCK_STREAM)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((ip, port))
            return sock
        except:
            sock.close()
            time.sleep(retry)


def send_message(socket: socket.socket, message: bytes):
    """
    Envoie un message sur le réseau
    :param socket le socket à utiliser pour envoyer le message
    :param message le message à envoyer en bytes
    """


def receive_message(socket: socket.socket) -> bytes:
    """
    Réceptionne un message sur le réseau
    :param socket le socket à utiliser pour réceptionner le message
    :return le message réceptionné en bytes
    """


def send_message_as_str(socket: socket.socket, message: str):
    """
    Envoie un message sur le réseau
    :param socket le socket à utiliser pour envoyer le message
    :param message le message à envoyer en tant que chaîne de caractères
    """


def receive_message_as_str(socket: socket.socket) -> str:
    """
    Réceptionne un message sur le réseau
    :param socket le socket à utiliser pour réceptionner le message
    :return le message réceptionné en tant que chaîne de caractères
    """

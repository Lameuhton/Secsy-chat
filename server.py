from common import network
import logging

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_server = logging.getLogger(__name__)

def main():

    sock_server = network.start_tcp_server("127.0.0.1", 4000)

    while True:
        # Attente connexion client
        sock_client, addr = sock_server.accept()
        logger_server.info(f"Connexion acceptee de {addr}")

        # Connexion avec client
        while True:
            message = network.receive_message_as_str(sock_client)
            if not message: #Client déconnecté
                break
            # Renvoie le message au client pour affichage
            network.send_message_as_str(sock_client, message)

        # Client déconnecté, on ferme le socket client
        sock_client.close()
        logger_server.info(f"Client {addr} deconnecte, attente d'une nouvelle connexion...")

if __name__ == "__main__":
    main()

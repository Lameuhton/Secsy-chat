from common import network
from threading import Thread, Lock
import logging

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_server = logging.getLogger(__name__)

# Dictionnaire pour stocker les clients connectés (dictionnaire plutot que liste pour retrouver facilement adresse/client)
clients_connectes = {}
# Verrou qui protègera clients_connectes
clients_lock = Lock()


def gerer_client(sock_client, addr): # Arguments générés dans le try

    with clients_lock: # Section critique protégée
        # Ajout du client dans le dictionnaire des clients connectés (contiendra des sockets)
        clients_connectes[addr] = sock_client # sock_client = connexion faite grâce à addr (ip, port)
        
        # Connexion avec client
        while True:
            message = network.receive_message_as_str(sock_client)
            if not message: # Client déconnecté
                break
            # Renvoie le message au client pour affichage

            # On utilise with comme ça le verrou se libère automatiquement à la fin du bloc, même en cas d'erreur (remplace le acquire et release)
            with clients_lock: 
                # .items() permet de récupérer d'un coup l'adresse (clé) et le socket (valeur) de chaque client.
                for client_addr, client_sock in clients_connectes.items(): 
                    network.send_message_as_str(client_sock, message)

            # Déconnexion du client, on sort de la boucle et on ferme le socket
            with clients_lock:
                del clients_connectes[addr]
            sock_client.close()
            logger_server.info(f"Client {addr} deconnecte, attente d'une nouvelle connexion...")


def main():

    sock_server = network.start_tcp_server("127.0.0.1", 4000)


    try:
        while True:
            # Attente connexion client
            sock_client, addr = sock_server.accept()
            logger_server.info(f"Connexion acceptee de {addr}")
            
            # Configuration du thread 
            # - target = fonction à exécuter
            # - args = arguments à passer à cette fonction
            # - daemon = True -> type de thread plus "discret", qui s'arrêtera automatiquement quand le programme principal se termine
            Thread(target=gerer_client, args=(sock_client, addr), daemon=True).start()

    except KeyboardInterrupt:
        logger_server.info("Arrêt du serveur")

    finally:
        # Fermeture propre du socket serveur pour éviter que le port 4000 reste occupé et bloque un redémarrage du seveur
        sock_server.close()

if __name__ == "__main__":
    main()

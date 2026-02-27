import logging
from queue import Queue, Empty
from threading import Thread
import time
from common import network
from secsychat_tui import SecsyChatTui, TuiMessage

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_client.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_client = logging.getLogger(__name__)

def handle_outbound_messages(q_outbound: Queue[TuiMessage], sock_client: network.socket.socket):
    """
    Traite les messages sortants et les renvoie vers l'interface pour affichage.
    """

    logger_client.info("Thread de traitement des messages sortants demarre")

    while not q_outbound.is_shutdown:
        try:
            # Récupération d'un message avec timeout de 0.5 seconde
            msg = q_outbound.get(timeout=0.5)
            # Traitement du message (affichage dans les logs pour l'instant)
            logger_client.info(f"{msg.sender_name}|{msg.message}")

            # Ici on ajoutera notre logique de traitement :
            # - Envoi vers un serveur
            # - Traitement cryptographique
            # - Sauvegarde dans une base de données
            # etc

            # Envoi du message vers le serveur
            network.send_message_as_str(sock_client, f"{msg.sender_name}|{msg.message}")

            # Marquage du message comme traité
            q_outbound.task_done()
        except Empty:
            # Timeout atteint, on reboucle pour vérifier is_shutdown
            continue
        except Exception as e:
            logger_client.error(f"Erreur lors du traitement d'un message sortant: {e}")
        
    logger_client.info("Thread de traitement des messages sortants s'arrete")


def handle_inbound_messages(q_inbound: Queue[TuiMessage], sock_client: network.socket.socket):
    """
    Traite les messages entrants et les renvoie vers l'interface pour affichage.
    """

    logger_client.info("Thread de traitement des messages entrants demarre")

    while not q_inbound.is_shutdown:
        try:
            # Récupération d'un message du serveur
            response = network.receive_message_as_str(sock_client)

            # Traitement du message (affichage dans les logs pour l'instant)
            logger_client.info(f"Message recu du serveur: {response}")

            # Envoi du message traité vers la queue inbound pour affichage dans l'interface
            parts = response.split('|', 1)
            username, content = parts
            heure = time.time()
            # On crée l'objet pour la TUI
            tui_msg = TuiMessage(sender_name=username, message=content,timestamp=heure)
            q_inbound.put(tui_msg)

        except Exception as e:
            logger_client.error(f"Erreur lors du traitement d'un message entrant: {e}")
        
    logger_client.info("Thread de traitement des messages entrants s'arrete")


def main():
    logger_client.info("Demarrage de l'application")

    pseudo = input("Entrez votre pseudo: ")
    if not pseudo:
        pseudo = "Anonyme"

    # Initialisation de la queue pour les messages reçus à afficher dans l'interface
    try:
        q_inbound = Queue[TuiMessage]()
        logger_client.debug("Queue inbound initialisee")
    except Exception as e:
        logger_client.error(f"Erreur de queue inbound: {e}")

    # Initialisation de la queue pour les messages envoyés depuis l'interface
    try:
        q_outbound = Queue[TuiMessage]()
        logger_client.debug("Queue outbound initialisee")
    except Exception as e:
        logger_client.error(f"Erreur de queue outbound: {e}")

    # Initialisation de l'interface (TUI)
    try:
        tui = SecsyChatTui(q_inbound, q_outbound, version="0.1.0", user_name=pseudo)
        logger_client.info("Interface TUI initialisee")
    except Exception as e:
        logger_client.error(f"Erreur de l'initialisation de la TUI: {e}")

    # Connexion au serveur
    try:
        sock_client = network.connect_tcp_server("127.0.0.1", 4000)
        logger_client.info("Connexion au serveur")

    except Exception as e:
        logger_client.error(f"Erreur lors de la connexion au serveur: {e}")
        return # Arrêt du programme si la connexion au serveur échoue


    # Création et lancement d'un thread permettant de gérer les messages envoyés
    try:
        # Configuration du thread pour messages sortants :
        # - target = fonction à exécuter
        # - args = arguments à passer à cette fonction
        # - daemon = True -> type de thread plus "discret", qui s'arrêtera automatiquement quand le programme principal se termine
        
        outbound_thread = Thread(
            target=handle_outbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages sortants
            args=(q_outbound, sock_client),
            daemon=True,
        )
        outbound_thread.start()

        logger_client.info("Thread de traitement des messages sortants lance")
    
    
        # Configuration du thread pour messages entrants :

        inbound_thread = Thread(
            target=handle_inbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages entrants
            args=(q_inbound, sock_client),
            daemon=True,
        )
        inbound_thread.start()
        
        logger_client.info("Thread de traitement des messages entrants lance")

    except Exception as e:
        logger_client.error(f"Thread d'envoi non correctement implemente: {e}")

    # Exécution de l'interface de chat (TUI)
    tui.run()
    logger_client.info("Lancement de l'interface")

    # Mise en arrêt des queues pour les messages reçus à afficher et les messages envoyés depuis l'interface
    if not q_inbound.is_shutdown:
        q_inbound.shutdown(immediate=True)
        logger_client.debug("Queue inbound arretee")

    if not q_outbound.is_shutdown:
        q_outbound.shutdown(immediate=True)
        logger_client.debug("Queue outbound arretee")

    # Attente de la fin du thread (join arrête le thread, timeout pour être sur qu'il n'attend pas indéfiniement)
    if outbound_thread.is_alive():
        outbound_thread.join(timeout=5.0)
        logger_client.debug("Thread outbound termine")

if __name__ == "__main__":
    main()

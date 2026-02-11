import logging
from queue import Queue, Empty
from threading import Thread

from secsychat_tui import SecsyChatTui, TuiMessage

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def handle_outbound_messages(q_outbound: Queue[TuiMessage]):
    """
    Fonction exécutée dans un thread pour traiter les messages envoyés depuis l'interface.
    """

    logger.info("Thread de traitement des messages sortants démarre")

    while not q_outbound.is_shutdown:
        try:
            # Récupération d'un message avec timeout de 0.5 seconde
            message = q_outbound.get(timeout=0.5)
            # Traitement du message (affichage dans les logs pour l'instant)
            logger.info(f"Message envoyé: {message}")

            # Ici on ajoutera notre logique de traitement :
            # - Envoi vers un serveur
            # - Traitement cryptographique
            # - Sauvegarde dans une base de données
            # etc

            # Marquage du message comme traité
            q_outbound.task_done()
        except Empty:
            # Timeout atteint, on reboucle pour vérifier is_shutdown
            continue
        except Exception as e:
            logger.error(f"Erreur lors du traitement d'un message sortant: {e}")

    logger.info("Thread de traitement des messages sortants s'arrête")

def main():
    logger.info("Demarrage de l'application")

    # Initialisation de la queue pour les messages reçus à afficher dans l'interface
    try:
        q_inbound = Queue[TuiMessage]()
        logger.debug("Queue inbound initialisee")
    except Exception as e:
        logger.error(f"Erreur de queue inbound: {e}")

    # Initialisation de la queue pour les messages envoyés depuis l'interface
    try:
        q_outbound = Queue[TuiMessage]()
        logger.debug("Queue outbound initialisee")
    except Exception as e:
        logger.error(f"Erreur de queue outbound: {e}")

    # Initialisation de l'interface (TUI)
    try:
        tui = SecsyChatTui(q_inbound, q_outbound, version="0.1.0")
        logger.info("Interface TUI initialisee")
    except Exception as e:
        logger.error(f"Erreur de l'initialisation de la TUI: {e}")

    # Création et lancement d'un thread permettant de gérer les messages envoyés
    try:
        # Configuration du thread 
        # - target = fonction à exécuter
        # - args = arguments à passer à cette fonction sous forme de tuple
        # - daemon = True -> thread s'arrêtera automatiquement quand le programme principal se termine

        outbound_thread = Thread(
            target=handle_outbound_messages,
            args=(q_outbound,),
            daemon=True,
        )
        outbound_thread.start()
        
        logger.info("Thread de traitement des messages sortants lancé")

    except Exception as e:
        logger.error(f"Thread d'envoi non correctement implémenté: {e}")

    # Exécution de l'interface de chat (TUI)
    tui.run()
    logger.info("Lancement de l'interface")

    # Mise en arrêt des queues pour les messages reçus à afficher et les messages envoyés depuis l'interface
    if not q_inbound.is_shutdown:
        q_inbound.shutdown(immediate=True)
        logger.debug("Queue inbound arretee")

    if not q_outbound.is_shutdown:
        q_outbound.shutdown(immediate=True)
        logger.debug("Queue outbound arretee")

    # Attente de la fin du thread (join arrête le thread, timeout pour être sur qu'il n'attend pas indéfiniement)
    if outbound_thread.is_alive():
        outbound_thread.join(timeout=5.0)
        logger.debug("Thread outbound termine")


if __name__ == "__main__":
    main()

import logging
from queue import Queue
from threading import Thread

from secsychat_tui import SecsyChatTui, TuiMessage

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Demarrage de l'application")

    # Initialisation de la queue pour les messages reçus à afficher dans l'interface
    try:
        q_inbound = Queue[TuiMessage]()
        logger.debug("Queue inbound initialisee")
    except:
        logger.error("Erreur de queue inbound")

    # Initialisation de la queue pour les messages envoyés depuis l'interface
    try:
        q_outbound = Queue[TuiMessage]()
        logger.debug("Queue outbound initialisee")
    except:
        logger.error("Erreur de queue outbound")

    # Initialisation de l'interface (TUI)
    try:
        tui = SecsyChatTui(q_inbound, q_outbound, version="0.1.0")
        logger.info("Interface TUI initialisee")
    except:
        logger.error("Erreur de l'initialisation de la queue TUI")

    # Création et lancement d'un thread permettant de gérer les messages envoyés
    try:
        a = 1 #A effacer
    except:
        logger.error("Thread d'envoi non correctement implémente")


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


if __name__ == "__main__":
    main()

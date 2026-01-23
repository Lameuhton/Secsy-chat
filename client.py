import logging
from queue import Queue
from threading import Thread

from secsychat_tui import SecsyChatTui, TuiMessage


def main():
    # Initialisation de la queue pour les messages reçus à afficher dans l'interface
    q_inbound = Queue[TuiMessage]()

    # Initialisation de la queue pour les messages envoyés depuis l'interface
    q_outbound = Queue[TuiMessage]()

    # Initialisation de l'interface (TUI)
    tui = SecsyChatTui(q_inbound, q_outbound, version="0.1.0")

    # Création et lancement d'un thread permettant de gérer les messages envoyés
    # TODO

    # Exécution de l'interface de chat (TUI)
    tui.run()

    # Mise en arrêt des queues pour les messages reçus à afficher et les messages envoyés depuis l'interface
    if not q_inbound.is_shutdown:
        q_inbound.shutdown(immediate=True)

    if not q_outbound.is_shutdown:
        q_outbound.shutdown(immediate=True)


if __name__ == "__main__":
    main()

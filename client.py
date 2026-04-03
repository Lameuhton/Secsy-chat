import logging
from queue import Queue, Empty
from threading import Thread
import time
from common import network, security, exchange
from secsychat_tui import SecsyChatTui, TuiMessage, TuiMessageType
from getpass import getpass
import json

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_client.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_client = logging.getLogger(__name__)

def handle_outbound_messages(q_outbound: Queue[TuiMessage], sock_client: network.socket.socket, aes_key: bytes):
    """
    Traite les messages sortants et les renvoie au serveur.
    """

    logger_client.info("Thread de traitement des messages sortants demarre")

    while not q_outbound.is_shutdown:
        try:
            # Récupération d'un message avec timeout de 0.5 seconde
            msg = q_outbound.get(timeout=0.5)
            # Traitement du message (affichage dans les logs pour l'instant)
            logger_client.info(f"Message envoyé au serveur:{msg.sender_name}|{msg.message}")

            # Ici on ajoutera notre logique de traitement :
            # - Envoi vers un serveur
            # - Traitement cryptographique
            # - Sauvegarde dans une base de données
            # etc
            
            # Vérification puis gestion du type de message reçu de la TUI
            match msg.type:
                # Simple message
                case TuiMessageType.MESSAGE:
                    # Construction du message JSON
                    message_dict = {
                        "timestamp": msg.timestamp,
                        "sender": {
                            "id": "", # vide car c'est le serveur qui le récupère par après
                            "name": msg.sender_name,
                        },
                        "recipient": {
                            "type": msg.type,
                            "id": "xxxxxxxxxxxxxxxxxxxxx",
                            "name": "X"
                        },
                        "payload": {
                            "cipher_text": msg.message,  # temporaire (pas encore RSA ici)
                            "cipher_text_size": len(msg.message),
                            "cipher_text_encrypted_key": "x"
                        },
                        "integrity": {
                            "checksum": "xxx",
                            "signature": "xxx"
                        }
                    }
        
            
            
            # Encodage du message en byte
            msg_bytes = message_dict.encode('utf-8')
            # Chiffrement du message avant envoi
            # Récupération des retours de la fonction aes_encrypt (tuple contenant nonce, cyphertext, tag)
            nonce, ciphertext, tag = security.aes_encrypt(msg_bytes, aes_key)
            # Préparation du payload (données qu'on veut envoyer), payload est en byte
            payload = nonce + tag + ciphertext
            # Envoi du payload (charge)
            network.send_message(sock_client, payload)

            # Marquage du message comme traité
            q_outbound.task_done()
        except Empty:
            # Timeout atteint, on reboucle pour vérifier is_shutdown
            continue
        except Exception as e:
            logger_client.error(f"Erreur lors du traitement d'un message sortant: {e}")
        
    logger_client.info("Thread de traitement des messages sortants s'arrete")


def handle_inbound_messages(q_inbound: Queue[TuiMessage], sock_client: network.socket.socket, aes_key: bytes):
    """
    Traite les messages entrants et les renvoie vers l'interface pour affichage.
    """

    logger_client.info("Thread de traitement des messages entrants demarre")

    while not q_inbound.is_shutdown:
        #try:

        # Récupération d'un message du serveur
        response = network.receive_message(sock_client)

        # Déchiffrement de la réponse
        # Récupère le nonce, tage et ciphertext (notre message chiffré)
        nonce = response[:12]
        tag = response[12:28]
        ciphertext = response[28:]
        
        # Déchiffre le message avec le nonce et le tag
        plaindata = security.aes_decrypt(ciphertext, aes_key, (nonce,tag))
        
        # Décode le message en str
        message = plaindata.decode('utf-8')
        
        # Traitement du message (affichage dans les logs pour l'instant)
        logger_client.info(f"Message recu du serveur: {message}")

        # Envoi du message traité vers la queue inbound pour affichage dans l'interface
        parts = message.split('|', 1)
        username, content = parts
        heure = time.time()
        # On crée l'objet pour la TUI
        tui_msg = TuiMessage(sender_name=username, message=content,timestamp=heure)
        q_inbound.put(tui_msg)

        #except Exception as e:
            #logger_client.error(f"Erreur lors du traitement d'un message entrant: {e}")
        
    logger_client.info("Thread de traitement des messages entrants s'arrete")


def main():
    logger_client.info("Demarrage de l'application")

    pseudo = input("Entrez votre pseudo: ")
    if not pseudo:
        pseudo = "Anonyme"

    password = getpass("Entrez votre mot de passe: ") # Pas de input pour pas qu'il soit marqué en "clair" dans l'interface utilisateur (on est en sécu quand-même...)

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

    
    # ECHANGE DIFFIE-HELLMAN
    
    # Réception de p et g du serveur
    p = int.from_bytes(network.receive_message(sock_client), byteorder='big')
    g = int.from_bytes(network.receive_message(sock_client), byteorder='big')

    # Recevoir, générer les clés et envoyer au serveur la publique
    peer_public_key = int.from_bytes(network.receive_message(sock_client), byteorder='big')
    private_key = security.diffie_hellman_generate_private_key(p)
    public_key = security.diffie_hellman_compute_public_key(private_key, p, g)
    network.send_message(sock_client, public_key.to_bytes(256, byteorder='big')) # Car send message envoie en bytes

    # Calculer clé partagée et clé AES
    shared_secret = security.diffie_hellman_compute_shared_secret(private_key, peer_public_key, p)
    aes_key = security.diffie_hellman_derive_shared_key(shared_secret, 32)  # 32 bytes = 256 bits


    # Envoi du <pseudonyme>|<mot de passe en clair> au serveur
    network.send_message_as_str(sock_client, f"{pseudo}|{password}") # Sensible au man in the middle mais l'énoncé le demande ainsi

    # Création et lancement de deux threads permettant de gérer les messages envoyés et reçus
    try:
        # Configuration du thread pour messages sortants :
        # - target = fonction à exécuter
        # - args = arguments à passer à cette fonction
        # - daemon = True -> type de thread plus "discret", qui s'arrêtera automatiquement quand le programme principal se termine
        
        outbound_thread = Thread(
            target=handle_outbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages sortants et aes
            args=(q_outbound, sock_client, aes_key),
            daemon=True,
        )
        outbound_thread.start()

        logger_client.info("Thread de traitement des messages sortants lance")
    

        # Configuration du thread pour messages entrants :

        inbound_thread = Thread(
            target=handle_inbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages entrants
            args=(q_inbound, sock_client, aes_key),
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

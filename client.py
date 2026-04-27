from queue import Queue, Empty
from threading import Thread
from common import network, security, exchange, message, event, statement
from secsychat_tui import SecsyChatTui, TuiMessage, TuiMessageSenderType, TuiMessageType
from getpass import getpass
import logging
import json
import os

import sys 
# sys.argv = liste qui contient les arguments passés au script
# Usage : python client.py <ip> <port> <pseudo>
# Exemple pour lancer le programme : python client.py 127.0.0.1 4000 Sophie
# sys.argv[0] → Nom du script (client.py)
# sys.argv[1] → Adresse IP : "127.0.0.1"
# sys.argv[2] → Port : "4000"
# sys.argv[3] → Pseudo : par exemple "Sophie"

# Chemins pour les clés RSA
# Problème : les chemins sont fixes et ne dépendent pas du pseudo --> Possibilité d'écraser mutuellement les clés.
# Conseil de solution : construire le chemin dans le main sur base du pseudo.
#KEYS_DIR = "keys"
#PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "private.pem")
#PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "public.pem")


# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_client.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_client = logging.getLogger(__name__)

def handle_outbound_messages(q_outbound: Queue[TuiMessage], sock_client: network.socket.socket, aes_key: bytes, public_keys: dict):
    """
    Traite les messages sortants et les renvoie au serveur.
    """

    while not q_outbound.is_shutdown:
        try:
            # Récupération d'un message avec timeout de 0.5 seconde
            msg = q_outbound.get(timeout=0.5)

            # Ici on ajoutera notre logique de traitement :
            # - Envoi vers un serveur
            # - Traitement cryptographique
            # - Sauvegarde dans une base de données
            # etc
            
            message_str = msg.message
            # Convertit le message en bytes pour le chiffrer
            plaintext = message_str.encode("utf-8")
            cipher_text_size = len(plaintext)
            
            # Génération d'une clé symétrique ChaCha (utilisé pour chiffrer le msg clair) à chaque msg 
            # --> symétrique = + rapide
            chacha_key = security.chacha_generate_key()
            # Chiffrement du message avec ChaCha
            nonce, ciphertext_with_tag = security.chacha_encrypt(plaintext, chacha_key)
            full_ciphertext = nonce + ciphertext_with_tag
            
            recipient_public_key = public_keys.get(msg.recipient_name)
            # Chiffrement asymétrique de la clé symétrique ChaCha par la clé publique du destinataire (RSA) --> chiffrement d'une clé de chiffrement
            encrypted_key = security.rsa_encrypt(chacha_key, recipient_public_key)

                
            # Construction du message JSON
            message_dict = {
                "timestamp": msg.timestamp,
                "sender": {
                    "id": msg.sender_name, 
                    "name": msg.sender_name,
                },
                "recipient": {
                    "type": msg.sender_type, # On peut faire ça car sender_type est un Enum
                    "id": "",
                    "name": ""
                },
                "payload": {
                    "cipher_text": full_ciphertext.hex(),  # On convertit en hex pour que ce soit du texte et pas des bytes
                    "cipher_text_size": cipher_text_size, # Sera utilisé pour la partie intégrité du message (checksum)
                    "cipher_text_encrypted_key": encrypted_key.hex()
                },
                "integrity": {
                    "checksum": "",
                    "signature": ""
                }
            }
              
            send_to_server(sock_client, aes_key, message_dict, exchange.ExchangeType.MESSAGE)

        except Empty:
            # Timeout atteint, on reboucle pour vérifier is_shutdown
            continue
        except Exception as e:
            logger_client.error(f"Erreur lors du traitement d'un message sortant: {e}")
        
    logger_client.info("Thread de traitement des messages sortants s'arrete")


def handle_inbound_messages(q_inbound: Queue[TuiMessage], sock_client: network.socket.socket, aes_key: bytes, tui: SecsyChatTui, private_key: bytes, public_keys: dict):
    """
    Traite les messages entrants et les renvoie vers l'interface pour affichage.
    :param q_inbound: la queue pour les messages entrants à afficher dans l'interface
    :param sock_client: la connexion au serveur pour recevoir les messages
    :param aes_key: la clé AES pour déchiffrer les messages reçus du serveur
    """

    while not q_inbound.is_shutdown:
        try:

            # Récupération d'un message du serveur
            response = network.receive_message(sock_client)

            # Récupère le type et le contenu de l'échange
            exchange_type = exchange.get_type(response)
            exchange_content = exchange.get_payload(response)
            
            # Déchiffrement du contenu de l'échange
            # Récupère le nonce, tage et ciphertext (notre message chiffré)
            nonce = exchange_content[:12]
            tag = exchange_content[12:28]
            ciphertext = exchange_content[28:]
            
            # Déchiffre avec le nonce et le tag
            plaindata = security.aes_decrypt(ciphertext, aes_key, (nonce,tag))
            
            # Vérification du type de message reçu
            if exchange_type == exchange.ExchangeType.MESSAGE:
                # Parse du message (JSON → dictionnaire Python)
                parsed_msg = message.parse_message(plaindata)
                # Récupération du payload chiffré et de la clé chiffrée
                payload = parsed_msg["payload"]
                full_ciphertext = bytes.fromhex(payload["cipher_text"])
                encrypted_key = bytes.fromhex(payload["cipher_text_encrypted_key"])
                # Séparer nonce et ciphertext+tag
                nonce = full_ciphertext[:12]
                ciphertext_with_tag = full_ciphertext[12:]
                # Déchiffrer la clé symétrique ChaCha avec la clé privée du client (RSA)
                chacha_key = security.rsa_decrypt(encrypted_key, private_key)
                # Déchiffrer le message avec la clé symétrique ChaCha
                plaintext = security.chacha_decrypt(ciphertext_with_tag, chacha_key, nonce)
                # Convertir le plaintext en string pour l'afficher
                message_str = plaintext.decode("utf-8")
                # Construction objet TuiMessage pour affichage dans l'interface
                tui_msg = TuiMessage(sender_name=parsed_msg["sender"]["name"], message=message_str, timestamp=parsed_msg["timestamp"])
                logger_client.info(f"Message reçu et affiché: {parsed_msg['sender']['name']} | {message_str}")
            
            elif exchange_type == exchange.ExchangeType.EVENT:
                # Parse de l'évènement (JSON → dictionnaire Python)
                parsed_event = event.parse_event(plaindata)
                
                # Vérification du type précis d'évènement et traitement spécifique si besoin

                # Si un utilisateur a été mis à jour
                if parsed_event["payload"]["name"] == "USER_UPDATED":
                    # Stockage de la clé publique de l'utilisateur dans le dictionnaire
                    name = parsed_event["payload"]["data"]["name"]
                    public_key_hex = parsed_event["payload"]["data"].get("public_key")

                    if public_key_hex:
                        public_keys[name] = bytes.fromhex(public_key_hex)
                        
                    # Vérification du status du tiers (actif ou inactif)
                    if parsed_event["payload"]["data"]["status"] == False:
                        logger_client.info(f"Utilisateur déconnecté: {parsed_event['payload']['data']['name']}")
                        # Construction de l'objet TuiMessage
                        tui_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"{parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], type=TuiMessageType.DISCONNECTED_USER_EVENT)
                        # Ajout du message à la queue
                        q_inbound.put(tui_msg)
                    else:
                        logger_client.info(f"Utilisateur connecté: {parsed_event['payload']['data']['name']}")
                        # Construction de l'objet TuiMessage        
                        tui_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"{parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], type=TuiMessageType.CONNECTED_USER_EVENT)
                        # Ajout du message à la queue
                        q_inbound.put(tui_msg)

                    # Pour éviter d'afficher une notification de connexion/déconnexion pour soi-même
                    if parsed_event["payload"]["data"]["name"] != tui.user_name:
                        if parsed_event["payload"]["data"]["status"]:
                            tui_system_msg = tui.create_system_message(f"L'utilisateur {parsed_event['payload']['data']['name']} est connecté")
                        else:
                            tui_system_msg = tui.create_system_message(f"L'utilisateur {parsed_event['payload']['data']['name']} est déconnecté")
                        q_inbound.put(tui_system_msg)

                # Si un canal a été créé ou rejoint
                if parsed_event["payload"]["name"] in ["CHANNEL_CREATED", "CHANNEL_JOINED"]:
                    
                    # Si le canal n'apparaissait pas dans la liste des canaux, il doit dorénavant y apparaitre
                    if parsed_event["payload"]["data"]["name"] not in tui.channels:
                        # Construction de l'objet TuiMessage
                        tui_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"{parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], type=TuiMessageType.NEW_CHANNEL_EVENT)
                        q_inbound.put(tui_msg)

                    # Affichage d'une notification spécifique selon que le canal a été créé ou rejoint
                    if parsed_event["payload"]["data"]["name"] == "CHANNEL_CREATED":
                        logger_client.info(f"Nouveau canal créé: {parsed_event['payload']['data']['name']}")
                        tui_channel_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"Le canal {parsed_event['payload']['data']['name']} a été créé", timestamp=parsed_event["timestamp"], sender_type=TuiMessageSenderType.CHANNEL)
                        q_inbound.put(tui_channel_msg)
                    else:
                        logger_client.info(f"{tui.user_name} - Canal rejoint: {parsed_event['payload']['data']['name']}")
                        tui_channel_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"Vous avez rejoint le canal {parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], sender_type=TuiMessageSenderType.CHANNEL)
                        q_inbound.put(tui_channel_msg)

                # Si un canal a été supprimé ou si un membre à été kick d'un canal
                if parsed_event["payload"]["name"] == "CHANNEL_DELETED":
                    # A faire plus tard: Adapter le contexte s'il pointait sur le cannal supprimé

                    # Vérification si un id et name sont présents dans data (user kick)
                    if parsed_event["payload"]["data"]["id"] and parsed_event["payload"]["data"]["name"]:
                        # Vérification si le membre éjecté est soi-même ou un autre membre du canal
                        if parsed_event["payload"]["data"]["member_id"] == tui.user_name:
                            tui_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"{parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], type=TuiMessageType.DELETED_CHANNEL_EVENT)
                            q_inbound.put(tui_msg)
                            # Plus tard - Changement de contexte
                            tui_channel_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"Vous avez été éjecté du canal {parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], sender_type=TuiMessageSenderType.CHANNEL)
                            q_inbound.put(tui_channel_msg)
                        else:
                            logger_client.info(f"{parsed_event['payload']['data']['member_name']} a été éjecté du canal {parsed_event['payload']['data']['name']}")
                            tui_channel_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"Le membre {parsed_event['payload']['data']['member_name']} a été éjecté du canal {parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], sender_type=TuiMessageSenderType.CHANNEL)
                            q_inbound.put(tui_channel_msg)

                    else:
                        tui_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"{parsed_event['payload']['data']['name']}", timestamp=parsed_event["timestamp"], type=TuiMessageType.DELETED_CHANNEL_EVENT)
                        q_inbound.put(tui_msg)
                        # Plus tard - Changement de contexte
                        tui_channel_msg = TuiMessage(sender_name=parsed_event["payload"]["data"]["name"], message=f"Le canal {parsed_event['payload']['data']['name'] } a été supprimé", timestamp=parsed_event["timestamp"], sender_type=TuiMessageSenderType.CHANNEL)
                        q_inbound.put(tui_channel_msg)

            else:
                logger_client.warning(f"Type d'échange inconnu reçu: {exchange_type}")
        

        except Exception as e:
            logger_client.error(f"Erreur lors du traitement d'un message entrant: {e}")
        
    logger_client.info("Thread de traitement des messages entrants s'arrete")

def send_to_server(sock, aes_key, data_dict: dict, exchange_type: exchange.ExchangeType):
    """
    Envoie un échange au serveur, en chiffrant les données et en ajoutant le type d'échange.

    :param sock: socket client
    :param aes_key: clé AES partagée
    :param data_dict: dictionnaire à envoyer (message, event, statement)
    :param exchange_type: type d'échange (MESSAGE, EVENT, STATEMENT)
    """
    try:
        # JSON → bytes
        json_bytes = json.dumps(data_dict).encode("utf-8")
        # Chiffrement AES
        nonce, ciphertext, tag = security.aes_encrypt(json_bytes, aes_key)
        # Construction du payload (nonce + tag + ciphertext)
        payload = nonce + tag + ciphertext
        # Ajout du type (IMPORTANT : .value)
        type_byte = str(exchange_type.value).encode()
        # Construction payload final (type + payload)
        final_payload = type_byte + payload

        # Envoi au serveur
        network.send_message(sock, final_payload)

    except Exception as e:
        logger_client.error(f"Erreur lors de l'envoi au serveur: {e}", exc_info=True)


def main():

    logger_client.info("Demarrage de l'application")

    #pseudo = input("Entrez votre pseudo: ")
    #if not pseudo:
    #    pseudo = "Anonyme"

    #Vérification du nombre d'arguments passés et sortie propre du programme si ce n'est pas le cas
    if len(sys.argv) != 4:
        print("Usage : python client.py <ip> <port> <pseudo>")
        sys.exit(1)

    #Affectation du pseudo par le passage d'argument à l'appel du programme
    pseudo = sys.argv[3]

    # Affection des chemins pour les clés
    private_key_path = f"{pseudo}.key"
    public_key_path  = f"{pseudo}.pub"  # L'énoncé mentionne uniquement cette pratique pour la clé privée (étendue à la clé publique).

    password = getpass("Entrez votre mot de passe: ") # Pas de input pour pas qu'il soit marqué en "clair" dans l'interface utilisateur (on est en sécu quand-même...)

    # Initialisation du dictionnaire pour stocker les clés publiques des autres utilisateurs (pour chiffrer les messages qu'on leur envoie)
    public_keys = {}
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
        sock_client = network.connect_tcp_server(sys.argv[1], int(sys.argv[2]))
        logger_client.info("Connexion au serveur")

    except Exception as e:
        logger_client.error(f"Erreur lors de la connexion au serveur: {e}")
        return # Arrêt du programme si la connexion au serveur échoue

    # -----------------------------------------------------------------
    # ECHANGE DIFFIE-HELLMAN
    # -----------------------------------------------------------------
    
    # Réception de p et g du serveur
    logger_client.debug("Attente de réception des paramètres p et g du serveur...")
    p = int.from_bytes(network.receive_message(sock_client), byteorder='big')
    g = int.from_bytes(network.receive_message(sock_client), byteorder='big')
    logger_client.debug("Paramètres p et g reçus du serveur")

    # Recevoir, générer les clés et envoyer au serveur la publique
    logger_client.debug("Attente de la clé publique du serveur...")
    peer_public_key = int.from_bytes(network.receive_message(sock_client), byteorder='big')
    logger_client.debug("Clé publique du serveur reçue")
    logger_client.debug("Génération de la clé privée et publique du client")
    private_key = security.diffie_hellman_generate_private_key(p)
    public_key = security.diffie_hellman_compute_public_key(private_key, p, g)
    network.send_message(sock_client, public_key.to_bytes(256, byteorder='big')) # Car send message envoie en bytes
    logger_client.debug("Clé publique du client envoyée au serveur")

    # Calculer clé partagée et clé AES
    logger_client.debug("Calcul du secret partagé et dérivation de la clé AES (256 bits)")
    shared_secret = security.diffie_hellman_compute_shared_secret(private_key, peer_public_key, p)
    aes_key = security.diffie_hellman_derive_shared_key(shared_secret, 32)  # 32 bytes = 256 bits
    logger_client.info("Échange Diffie-Hellman terminé — clé AES établie")

    # -----------------------------------------------------------------
    # AUTHENTIFICATION
    # -----------------------------------------------------------------
    
    # Envoi du <pseudonyme>|<mot de passe en clair> au serveur
    network.send_message_as_str(sock_client, f"{pseudo}|{password}") # Sensible au man in the middle mais l'énoncé le demande ainsi

    # -----------------------------------------------------------------
    # GENERATION RSA
    # -----------------------------------------------------------------
    
    # Crée le dossier des clés s'il n'existe pas --> Pas besoin de créer un répertoire (Voir énoncé)
    # os.makedirs(KEYS_DIR, exist_ok=True)
    
    # Si les clés existent → on les charge
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        with open(private_key_path, "rb") as f:
            private_key = f.read()

        with open(public_key_path, "rb") as f:
            public_key = f.read()
    # Sinon → on les génère et on les sauvegarde pour les réutiliser lors de la prochaine connexion
    else:
        # Génération des clés
        private_key, public_key = security.rsa_generate_keypair()

        # Sauvegarde
        with open(private_key_path, "wb") as f:
            f.write(private_key)

        with open(public_key_path, "wb") as f:
            f.write(public_key)
            
    # Envoi de la clé publique au serveur pour qu'il puisse l'utiliser pour chiffrer les messages destinés à ce client
    network.send_message(sock_client, public_key)
    
    
    # Envoi d'une instruction GET_USERS pour récupérer la liste des utilisateurs actifs et les afficher dans l'interface    
    get_users_statement = statement.build_get_users()
    send_to_server(sock_client, aes_key, get_users_statement, exchange.ExchangeType.STATEMENT)

    # Création et lancement de deux threads permettant de gérer les messages envoyés et reçus
    try:
        # Configuration du thread pour messages sortants :
        # - target = fonction à exécuter
        # - args = arguments à passer à cette fonction
        # - daemon = True -> type de thread plus "discret", qui s'arrêtera automatiquement quand le programme principal se termine
        
        outbound_thread = Thread(
            target=handle_outbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages sortants et aes
            args=(q_outbound, sock_client, aes_key, public_keys),
            daemon=True,
        )
        outbound_thread.start()

        logger_client.info("Thread de traitement des messages sortants lance")
    

        # Configuration du thread pour messages entrants :

        inbound_thread = Thread(
            target=handle_inbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages entrants
            args=(q_inbound, sock_client, aes_key, tui, private_key, public_keys),
            daemon=True,
        )
        inbound_thread.start()
        
        logger_client.info("Thread de traitement des messages entrants lance")

    except Exception as e:
        logger_client.error(f"Thread d'envoi non correctement implemente: {e}")

    # Exécution de l'interface de chat (TUI)
    tui.run()
    logger_client.info("Lancement de l'interface")

    # Envoi d'une instruction UPDATE_USER pour signaler au serveur que ce client est inactif (s'est déconnecté)
    update_user_statement = statement.build_update_user(False) 
    send_to_server(sock_client, aes_key, update_user_statement, exchange.ExchangeType.STATEMENT)

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

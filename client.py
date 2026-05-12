from queue import Queue, Empty
from threading import Thread
from common import network, security, exchange, message, event, statement
from secsychat_tui import SecsyChatTui, TuiMessage, TuiMessageSenderType, TuiMessageType
from getpass import getpass
import logging
import json
import ipaddress
import os
import sys
import re #regex

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

def handle_outbound_messages(q_outbound: Queue[TuiMessage], sock_client: network.socket.socket, aes_key: bytes, client_connectes: dict, channels: dict, context_data: dict):
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
            
            message_str = msg.message.strip()
            
            # -------------------------------------------------
            # COMMANDES
            # -------------------------------------------------
            if message_str.startswith("/"):
                
                parts = message_str.split()
                command = parts[0].lower()
                
                # ---------------- JOIN ----------------
                if command == "/join":
                    # Vérification des arguments donnés
                    if len(parts) < 2 or len(parts) > 3:
                        logger_client.warning("Commande /join invalide. Usage: /join <channel_name> <optionnel: secret>")
                        continue
                    
                    channel_name = parts[1]
                    
                    # Si un secret est donné, on l'inclut dans l'instruction JOIN_CHANNEL
                    if len(parts) == 3:
                        secret = parts[2]
                        join_statement = statement.build_join_channel(channel_name, secret)
                    else:
                        join_statement = statement.build_join_channel(channel_name)

                    # Envoi JOIN_CHANNEL au serveur
                    send_to_server(sock_client, aes_key, join_statement, exchange.ExchangeType.STATEMENT)
                    # Envoi GET_LAST_MESSAGES pour récupérer les derniers messages de ce channel
                    get_last_messages_statement = statement.build_get_last_messages(channel_name, 20)
                    send_to_server(sock_client, aes_key, get_last_messages_statement, exchange.ExchangeType.STATEMENT)
                
                # ---------------- NEW ----------------
                elif command == "/new":
                    
                    # Vérification des arguments donnés
                    if len(parts) != 3:
                        logger_client.warning("Commande /new invalide. Usage: /new <channel_name> <secret>")
                        continue
                    
                    channel_name = parts[1]
                    secret = parts[2]
                    
                    # Construction CREATE_CHANNEL et envoi au serveur
                    create_statement = statement.build_create_channel(channel_name, secret)
                    send_to_server(sock_client, aes_key, create_statement, exchange.ExchangeType.STATEMENT)
                    
                # ---------------- LEAVE ----------------
                elif command == "/leave":
                    # Vérification des arguments donnés
                    if len(parts) != 2:
                        logger_client.warning("Commande /leave invalide. Usage: /leave <channel_name>")
                        continue
                    
                    channel_name = parts[1]
                    
                    # Construction LEAVE_CHANNEL et envoi au serveur
                    leave_statement = statement.build_leave_channel(channel_name)
                    send_to_server(sock_client, aes_key, leave_statement, exchange.ExchangeType.STATEMENT)
                
                # ---------------- KICK ----------------
                elif command == "/kick":
                    # Vérification des arguments donnés
                    if len(parts) != 3:
                        logger_client.warning("Commande /kick invalide. Usage: /kick <channel_name> <user_name>")
                        continue
                    
                    channel_name = parts[1]
                    user_name = parts[2]
                    
                    # Construction KICK_CHANNEL_MEMBER et envoi au serveur
                    kick_statement = statement.build_kick_channel_member(channel_name, user_name)
                    send_to_server(sock_client, aes_key, kick_statement, exchange.ExchangeType.STATEMENT)

                # ---------------- DELETE ----------------
                elif command == "/delete":
                    # Vérification des arguments donnés
                    if len(parts) != 2:
                        logger_client.warning("Commande /delete invalide. Usage: /delete <channel_name>")
                        continue
                    
                    channel_name = parts[1]
                    
                    # Construction DELETE_CHANNEL et envoi au serveur
                    delete_statement = statement.build_delete_channel(channel_name)
                    send_to_server(sock_client, aes_key, delete_statement, exchange.ExchangeType.STATEMENT)

                else:
                    logger_client.warning(f"Commande inconnue: {command}")
                    continue

            # -------------------------------------------------
            # MESSAGES CHANNEL
            # -------------------------------------------------
            else:
            
                # Vérification du contexte
                context_id = context_data.get("context")
                    
                if not context_id:
                    logger_client.warning("Aucun contexte de chat sélectionné pour l'envoi du message! Veuillez rejoindre un canal avant d'envoyer un message.")
                    continue
                    
                # Récupération du nom du channel
                channel_name = None
                for name, info in channels.items():
                    if info["id"] == context_id:
                        channel_name = name
                        break
                if not channel_name:
                    logger_client.warning(f"Contexte invalide: channel {context_id} introuvable.")
                    continue
                
                # Chiffrement du message à envoyer
                # Convertit le message en bytes pour le chiffrer
                plaintext = message_str.encode("utf-8")
                cipher_text_size = len(plaintext)
            
                # Génération d'une clé symétrique ChaCha (utilisé pour chiffrer le msg clair) à chaque msg 
                # --> symétrique = + rapide
                chacha_key = security.chacha_generate_key()
                # Chiffrement du message avec ChaCha
                nonce, ciphertext_with_tag = security.chacha_encrypt(plaintext, chacha_key)
                full_ciphertext = nonce + ciphertext_with_tag
                
                recipient_public_key = channels[channel_name]["public_key"]
                # Chiffrement asymétrique de la clé symétrique ChaCha par la clé publique du destinataire (RSA) --> chiffrement d'une clé de chiffrement
                encrypted_key = security.rsa_encrypt(chacha_key, recipient_public_key)

                # Construction du message à envoyer au serveur
                sender_name = msg.sender_name
                sender_id = client_connectes[sender_name]["id"]
                
                message_dict = message.build_message(msg.timestamp, sender_id, sender_name, context_id, channel_name, "CHANNEL", full_ciphertext.hex(), cipher_text_size, encrypted_key.hex())
                send_to_server(sock_client, aes_key, message_dict, exchange.ExchangeType.MESSAGE)

        except Empty:
            # Timeout atteint, on reboucle pour vérifier is_shutdown
            continue
        except Exception as e:
            logger_client.error(f"Erreur lors du traitement d'un message sortant: {e}")
        
    logger_client.info("Thread de traitement des messages sortants s'arrete")


def handle_inbound_messages(q_inbound: Queue[TuiMessage], sock_client: network.socket.socket, aes_key: bytes, tui: SecsyChatTui, private_key: bytes, client_connectes: dict, channels: dict, context_data: dict):
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
                time_stamp = parsed_msg["timestamp"]
                sender_name = parsed_msg["sender"]["name"]
                sender_id = parsed_msg["sender"]["id"]
                recipient_type = parsed_msg["recipient"]["type"]
                recipient_name = parsed_msg["recipient"]["name"]
                
                # Vérification si c'est un message channel ou privé
                if recipient_type == "CHANNEL":
                    # Si le message reçu concerne le canal actuellement sélectionné dans le contexte, on l'affiche dans l'interface
                    if parsed_msg["recipient"]["id"] == context_data.get("context"):
                        # On déchiffre et on construit le message
                        
                        message_str = security.decrypt_message(parsed_msg, channels[recipient_name]["private_key"])
                        tui_msg = TuiMessage(timestamp=time_stamp, sender_name=sender_name, message=message_str, channel=recipient_name)
                        q_inbound.put(tui_msg)
                    else:
                        continue
                    
                elif recipient_type == "USER":
                    # On déchiffre et on construit le message
                    message_str = security.decrypt_message(parsed_msg, private_key)
                    # Construction objet TuiMessage pour affichage dans l'interface
                    tui_msg = TuiMessage(timestamp=time_stamp, sender_name=sender_name, message=message_str)
                    q_inbound.put(tui_msg)
                
            elif exchange_type == exchange.ExchangeType.EVENT:
                # Parse de l'évènement (JSON → dictionnaire Python)
                parsed_event = event.parse_event(plaindata)
                
                # Vérification du type précis d'évènement et traitement spécifique si besoin

                # Si un utilisateur a été mis à jour
                if parsed_event["payload"]["name"] == "USER_UPDATED":

                    time_stamp = parsed_event["timestamp"]
                    name = parsed_event["payload"]["data"]["name"]
                    user_id = parsed_event["payload"]["data"]["id"]
                    user_public_key = bytes.fromhex(parsed_event["payload"]["data"]["public_key"])
                    status = parsed_event["payload"]["data"]["status"]
                        
                    # Vérification du status du tiers (actif ou inactif)
                    if status == False:
                        logger_client.info(f"Utilisateur déconnecté: {name}")
                        # Retire l'utilisateur du dictionnaire
                        if name in client_connectes:
                            del client_connectes[name]
                        # Construction de l'objet TuiMessage
                        tui_msg = TuiMessage(sender_name=name, message=f"{name}", timestamp=time_stamp, type=TuiMessageType.DISCONNECTED_USER_EVENT)
                        # Ajout du message à la queue
                        q_inbound.put(tui_msg)
                    else:
                        logger_client.info(f"Utilisateur connecté: {name}")
                        # Rajoute l'utilisateur dans le dictionnaire s'il n'y est pas déjà
                        if name not in client_connectes:
                            client_connectes[name] = {"id": user_id, "public_key": user_public_key}
                        # Construction de l'objet TuiMessage        
                        tui_msg = TuiMessage(sender_name=name, message=f"{name}", timestamp=time_stamp, type=TuiMessageType.CONNECTED_USER_EVENT)
                        # Ajout du message à la queue
                        q_inbound.put(tui_msg)

                    # Pour éviter d'afficher une notification de connexion/déconnexion pour soi-même
                    if name != tui.user_name:
                        if status:
                            tui_system_msg = tui.create_system_message(f"L'utilisateur {name} est connecté")
                        else:
                            tui_system_msg = tui.create_system_message(f"L'utilisateur {name} est déconnecté")
                        q_inbound.put(tui_system_msg)

                # Si un canal a été créé ou rejoint
                if parsed_event["payload"]["name"] in ["CHANNEL_CREATED", "CHANNEL_JOINED"]:
                    
                    channel_name = parsed_event["payload"]["data"]["name"]
                    channel_id = parsed_event["payload"]["data"]["id"]
                    channel_public_key =  bytes.fromhex(parsed_event["payload"]["data"]["public_key"])
                    time_stamp = parsed_event["timestamp"]
                    
                    # Si le canal n'apparaissait pas dans la liste des canaux, il doit dorénavant y apparaitre
                    if channel_name not in tui.channels:
                        # Construction de l'objet TuiMessage
                        tui_msg = TuiMessage(sender_name=channel_name, message=f"{channel_name}", timestamp=time_stamp, type=TuiMessageType.NEW_CHANNEL_EVENT)
                        q_inbound.put(tui_msg)

                        

                    # Affichage d'une notification spécifique selon que le canal a été créé ou rejoint
                    if parsed_event["payload"]["name"] == "CHANNEL_CREATED":
                        # Ne pas changer le contexte ici 
                        logger_client.info(f"Nouveau canal créé: {channel_name}")
                        # Construction de l'objet TuiMessage
                        tui_channel_msg = TuiMessage(sender_name=channel_name, message=f"Le canal {channel_name} a été créé", timestamp=time_stamp, sender_type=TuiMessageSenderType.CHANNEL)
                        q_inbound.put(tui_channel_msg)
                    else:
                        # Changer le contexte ici
                        context_data["context"] = channel_id
                        with open(f"{tui.user_name}.json", "w", encoding="utf-8") as f:
                            json.dump(context_data, f)
                            
                        logger_client.info(f"{tui.user_name} - Canal rejoint: {channel_name}")
                        tui_channel_msg = TuiMessage(sender_name=channel_name, message=f"Vous avez rejoint le canal {channel_name}", timestamp=time_stamp, sender_type=TuiMessageSenderType.CHANNEL)
                        q_inbound.put(tui_channel_msg)
                    
                    # Rajoute la canal dans le dictionnaire avec la clé privée si donnée
                    if channel_name not in channels:
                        channels[channel_name] = {}

                    channels[channel_name]["id"] = channel_id
                    channels[channel_name]["public_key"] = channel_public_key

                    if "private_key" in parsed_event["payload"]["data"]:
                        channels[channel_name]["private_key"] = bytes.fromhex(
                            parsed_event["payload"]["data"]["private_key"]
                        )

                # Si un canal a été supprimé ou si un membre à été kick d'un canal
                if parsed_event["payload"]["name"] == "CHANNEL_DELETED":
                    
                    time_stamp = parsed_event["timestamp"]
                    channel_name = parsed_event["payload"]["data"]["name"]
                    
                    # Vérification si un member_id et member_name sont présents dans data (user kick)
                    if parsed_event["payload"]["data"]["member_id"] and parsed_event["payload"]["data"]["member_name"]:
                        member_id = parsed_event["payload"]["data"]["member_id"]
                        member_name = parsed_event["payload"]["data"]["member_name"]
                        
                        # Vérification si le membre éjecté est soi-même ou un autre membre du canal
                        if member_name == tui.user_name:
                            tui_msg = TuiMessage(sender_name=channel_name, message=f"{channel_name}", timestamp=time_stamp, type=TuiMessageType.DELETED_CHANNEL_EVENT)
                            q_inbound.put(tui_msg)
                            # Supprimer le contexte et le laisser vide
                            context_data["context"] = ""
                            with open(f"{tui.user_name}.json", "w", encoding="utf-8") as f:
                                json.dump(context_data, f)
                                
                            tui_channel_msg = TuiMessage(sender_name=channel_name, message=f"Vous avez été éjecté du canal {channel_name}", timestamp=time_stamp, sender_type=TuiMessageSenderType.CHANNEL)
                            q_inbound.put(tui_channel_msg)
                            # Retire le canal du dictionnaire des canaux
                            if channel_name in channels:
                                del channels[channel_name]
                        else:
                            # Ne pas supprimer le contexte
                            tui_channel_msg = TuiMessage(sender_name=channel_name, message=f"Le membre {member_name} a été éjecté du canal {channel_name}", timestamp=time_stamp, sender_type=TuiMessageSenderType.CHANNEL)
                            q_inbound.put(tui_channel_msg)
                            
                    # Sinon, le canal a été supprimé
                    else:
                        # Vérifier si le canal supprimé est dans le dictionnaire des canaux
                        if channel_name in channels:
                            # Vérification si le canal supprimé est le canal actuellement sélectionné dans le contexte
                            if channels[channel_name]["id"] == context_data.get("context"):
                                # Supprimer le contexte et le laisser vide
                                context_data["context"] = ""
                                with open(f"{tui.user_name}.json", "w", encoding="utf-8") as f:
                                    json.dump(context_data, f)
                            # Supprimer le canal de l'interface
                            tui_msg = TuiMessage(sender_name=channel_name, message=f"{channel_name}", timestamp=time_stamp, type=TuiMessageType.DELETED_CHANNEL_EVENT)
                            q_inbound.put(tui_msg)
                            tui_channel_msg = TuiMessage(sender_name=channel_name, message=f"Le canal {channel_name} a été supprimé", timestamp=time_stamp, sender_type=TuiMessageSenderType.CHANNEL)
                            q_inbound.put(tui_channel_msg)
                            # Retire le canal du dictionnaire des canaux
                            if channel_name in channels:
                                del channels[channel_name]
                        # Sinon ignorer le message
                        else:
                            continue        
                        
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

def is_valid_ip(ip):
    """Vérifie si l'adresse IP est valide"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False
    
def is_valid_port(port):
    """Vérifie si le port est valide (entre 0 et 65535)"""
    try:
        port = int(port)
        return 0 <= port <= 65535
    except ValueError:
        return False

def is_valid_pseudo(pseudo):
    """Vérifie si le pseudo est valide (2 à 20 caractères, lettres, chiffres, underscores et tirets autorisés)"""
    return re.match(r'^[a-zA-Z0-9_-]{2,20}$', pseudo) is not None

def main():

    logger_client.info("Demarrage de l'application")

    #Vérification du nombre d'arguments passés et sortie propre du programme si ce n'est pas le cas
    if len(sys.argv) != 4:
        print("Usage : python client.py <ip> <port> <pseudo>")
        sys.exit(1)

    ip = sys.argv[1]
    port = sys.argv[2]
    pseudo = sys.argv[3]

    if not is_valid_ip(ip):
        print("IP invalide")
        sys.exit(1)

    if not is_valid_port(port):
        print("Port invalide")
        sys.exit(1)

    if not is_valid_pseudo(pseudo):
        print("Pseudo invalide (2-20 caractères alphanumériques)")
        sys.exit(1)

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
    
    # Affection du chemin pour la clé privée
    private_key_path = f"{pseudo}.key"
    
    # Si la clé privée existe → on la charge
    if os.path.exists(private_key_path):
        with open(private_key_path, "rb") as f:
            private_key = f.read()

    # Sinon → on génère une paire de clé et on sauvegarde la privée et on envoie la publique au serveur
    else:
        # Génération des clés (en bytes)
        private_key, public_key = security.rsa_generate_keypair()

        # Sauvegarde
        with open(private_key_path, "wb") as f:
            f.write(private_key)
            
        # Envoi de la clé publique au serveur pour qu'il puisse l'utiliser pour chiffrer les messages destinés à ce client
        network.send_message(sock_client, public_key.hex().encode("utf-8"))
    
    # -------------------------------------------------
    # CHARGEMENT CONTEXTE
    # -------------------------------------------------
    
    # Variable qui contiendra le contexte du chat
    context_path = f"{pseudo}.json"
    
    # Si un contexte existe déjà pour ce pseudo, on le charge
    if os.path.exists(context_path):
        # Mode d'ouverture "r" pour read,
        # on lit le fichier et on charge le contenu JSON
        with open(context_path, "r", encoding="utf-8") as f:
            context_data = json.load(f)
    # Sinon, on crée le fichier avec un contexte vide
    else:
        context_data = {"context": ""}
        # Mode d'ouvreture "w" pour write, on crée le fichier s'il n'existe pas
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context_data, f)

    
    
    # Contiendra les id, name et clé publiques des utilisateurs connectés
    client_connectes = {}
    # Contiendra les id, name, clé publiques et optionnellement la clé privée (si on est membre) des channels pour cette session
    channels = {}
    
    # -------------------------------------------------
    # INSTRUCTIONS DE BASE AU SERVEUR
    # -------------------------------------------------
    
    # Envoi d'une instruction GET_USERS pour récupérer la liste des utilisateurs actifs et les afficher dans l'interface    
    get_users_statement = statement.build_get_users()
    send_to_server(sock_client, aes_key, get_users_statement, exchange.ExchangeType.STATEMENT)
    
    # Envoi d'une instruction GET_CHANNELS pour récupérer la liste des canaux dont l'utilisateur est membre
    get_channels_statement = statement.build_get_channels()
    send_to_server(sock_client, aes_key, get_channels_statement, exchange.ExchangeType.STATEMENT)
    
    # Récupération du nom du channel
    channel_name = ""

    for name, info in channels.items():
        if info["id"] == context_data["context"]:
            channel_name = name
            break

    # Envoi d'une instruction GET_LAST_MESSAGES pour récupérer les 20 derniers messages du channel et privés
    get_last_messages_statement = statement.build_get_last_messages(channel_name, 20)
    send_to_server(sock_client, aes_key, get_last_messages_statement, exchange.ExchangeType.STATEMENT)
   
    # ------------------------------------------------
    # LANCEMENT DES THREADS ET DE L'INTERFACE
    # ------------------------------------------------
    
    # Création et lancement de deux threads permettant de gérer les messages envoyés et reçus
    try:
        # Configuration du thread pour messages sortants :
        # - target = fonction à exécuter
        # - args = arguments à passer à cette fonction
        # - daemon = True -> type de thread plus "discret", qui s'arrêtera automatiquement quand le programme principal se termine
        
        outbound_thread = Thread(
            target=handle_outbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages sortants et aes
            args=(q_outbound, sock_client, aes_key, client_connectes, channels, context_data),
            daemon=True,
        )
        outbound_thread.start()

        logger_client.info("Thread de traitement des messages sortants lance")
    

        # Configuration du thread pour messages entrants :

        inbound_thread = Thread(
            target=handle_inbound_messages,
            # On passe les queues et le socket client en arguments à la fonction de traitement des messages entrants
            args=(q_inbound, sock_client, aes_key, tui, private_key, client_connectes, channels, context_data),
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

import json
import time
from common import network, database, data, security, exchange, message, statement, event
from threading import Thread, Lock
import logging


DB_PATH = "database.db"

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_server = logging.getLogger(__name__)

# Dictionnaire pour stocker les clients connectés (dictionnaire plutot que liste pour retrouver facilement adresse/client)
clients_connectes = {}
# Dictionnaire pour stocker les channels existants
channels = {}
# Verrou qui protègera clients_connectes
clients_lock = Lock()


def send_msg_to_clients(plaindata: dict, exchange_type: exchange.ExchangeType, clients_dict):
    """
    Fonction pour renvoyer un message à tous les clients connectés. Le message est d'abord converti en JSON puis en bytes avant d'être chiffré et envoyé.
    
    :param plaindata: le message en clair à renvoyer aux clients (dictionnaire Python)
    :param exchange_type: le type d'échange du message
    :param clients_dict: le dictionnaire des clients à qui envoyer le message
    """
    try:
    # On utilise with comme ça le verrou se libère automatiquement à la fin du bloc, même en cas d'erreur (remplace le acquire et release)
        with clients_lock: 
            # .items() permet de récupérer d'un coup l'adresse (clé) et le socket (valeur) de chaque client ainsi que leur clé AES associée
            for addr, client_data in clients_dict.items():

                client_sock = client_data["sock"]
                client_key = client_data["aes_key"]
                
                json_bytes = json.dumps(plaindata).encode('utf-8') # Convertit le message en JSON puis en bytes
                # Rechiffre le message avec la clé AES de chaque client
                nonce, cyphertext, tag = security.aes_encrypt(json_bytes, client_key)
                # Préparation du payload (nonce, tag, ciphertext concaténés)
                payload_renvoi = nonce + tag + cyphertext
                # Ajout du type du message
                type_byte = str(exchange_type.value).encode() # Convertit le type d'échange en byte pour l'inclure dans le message envoyé
                final_payload = type_byte + payload_renvoi
                # Renvoi du payload au(x) client(x) (en byte car le payload est en byte)
                network.send_message(client_sock, final_payload)
    except Exception as e:
        logger_server.error(f"Erreur lors de l'envoie du message aux clients: {e}", exc_info=True)

def gerer_client(sock_client, addr): # Arguments générés dans le try

    # ------------------------------------------------------------
    # DIFFIE-HELLMAN
    # ------------------------------------------------------------
    # Générer les paramètres de la clé publique
    # Envoi de p et g au client
    logger_server.debug("Génération des paramètres publics Diffie-Hellman (p, g) - 2048 bits")
    p, g = security.diffie_hellman_generate_public_parameters(2048)
    logger_server.debug(f"Paramètres générés — envoi de p ({len(p.to_bytes(256, byteorder='big'))} bytes) et g au client {addr}")
    network.send_message(sock_client, p.to_bytes(256, byteorder='big')) # 2048 bits // 8 = 256 bytes
    network.send_message(sock_client, g.to_bytes(8, byteorder='big')) # Presque tjrs 2 ou 5 donc 8 bytes
    logger_server.debug(f"p et g envoyés à {addr}")

    # Générer les clés et envoyer au client la publique
    logger_server.debug("Génération de la clé privée et publique du serveur")
    private_key = security.diffie_hellman_generate_private_key(p)
    public_key = security.diffie_hellman_compute_public_key(private_key, p, g)
    network.send_message(sock_client, public_key.to_bytes(256, byteorder='big')) # Car send message envoie en bytes
    logger_server.debug(f"Clé publique du serveur envoyée à {addr}")

    # Recevoir clé publ du client et calculer clé partagée + clé AES
    logger_server.debug(f"Attente de la clé publique du client {addr}...")
    peer_public_key = int.from_bytes(network.receive_message(sock_client), byteorder='big') # Clé publique du client != clé publ du serveur
    logger_server.debug(f"Clé publique reçue de {addr}")
    logger_server.debug("Calcul du secret partagé et dérivation de la clé AES (256 bits)")
    shared_secret = security.diffie_hellman_compute_shared_secret(private_key, peer_public_key, p)
    aes_key = security.diffie_hellman_derive_shared_key(shared_secret, 32)  # 32 bytes = 256 bits
    logger_server.info(f"Échange Diffie-Hellman terminé avec {addr} — clé AES établie")

    # ------------------------------------------------------------
    # AUTHENTIFICATION
    # ------------------------------------------------------------ 
    # Premier message = authentification (avant la boucle)
    premier_message = network.receive_message_as_str(sock_client)
    pseudo, password = premier_message.split("|") # Car on l'a mis en forme <pseudo>|<paswd>
    
    
    # Vérification de l'existence de l'utilisateur et du mot de passe
    if not data.user_exists(pseudo):
        public_key = network.receive_message(sock_client)
        hashed_password = security.argon2_hash_password(password)
        user_id = data.create_user(pseudo, hashed_password, public_key.decode('utf-8'))
        logger_server.info(f"Nouvel utilisateur créé : {pseudo}")
    else:
        user = data.get_user(pseudo)
        user_id = user[0]
        public_key = user[3]
        verif_mdp = user[2] # Car user = (id, name, secret, public_key, created_at, last_activity_at)
        if not security.argon2_verify_password(password, verif_mdp): # Fonction retourne True/False
            logger_server.warning(f"Tentative de connexion échouée pour : {pseudo}")
            sock_client.close()
            return # Permet de ne pas rentrer dans la boucle suivante si le client n'a pas rentré le bon mdp
        logger_server.info(f"Utilisateur authentifié : {pseudo}")

    # ------------------------------------------------------------
    # AJOUT DU CLIENT AU DICTIONNAIRE DES CLIENTS CONNECTES + ENVOI D'UN EVENEMENT DE CONNEXION A TOUS LES CLIENTS
    # ------------------------------------------------------------
    with clients_lock: # Section critique protégée
        # Ajout du client, de sa clé AES et de son pseudo dans le dictionnaire des clients connectés (contiendra des sockets + clés AES)
        clients_connectes[addr] = {
            "sock": sock_client,
            "aes_key": aes_key,
            "pseudo": pseudo,
            "id": user_id,
            "public_key": public_key
        }
        # sock_client = connexion faite grâce à addr (ip, port), aes_key = clé de chiffrement symétrique partagée entre le serveur et ce client
    
    # Envoi à tous les clients d'un événement USER_UPDATED avec le pseudo et le status du client qui vient de se connecter
    event_payload = event.build_user_updated(time.time(), pseudo, pseudo, True, public_key)
    send_msg_to_clients(event_payload, exchange.ExchangeType.EVENT, clients_connectes)

    # ------------------------------------------------------------
    # GESTION DES MESSAGES RECUS
    # (RECEPTION, DECHIFFREMENT, RECHIFFREMENT, RENVOI)
    # ------------------------------------------------------------
    while True:
        response = network.receive_message(sock_client)
        
        # Client déconnecté
        if not response:
            logger_server.info(f"{pseudo} déconnecté brutalement")
            event_payload = event.build_user_updated(time.time(), pseudo, pseudo, False, public_key)
            send_msg_to_clients(event_payload, exchange.ExchangeType.EVENT, clients_connectes)
            break
        
        # Récupère le type et le contenu de l'échange
        exchange_type = exchange.get_type(response)
        exchange_content = exchange.get_payload(response)
        
        # Récupère le nonce, tag et ciphertext (ciphertext = notre message chiffré)
        # Les tailles du nonce et du tag sont fixes (12 bytes pour le nonce et 16 bytes pour le tag en AES-GCM), donc on peut les découper facilement
        # Le reste après le tag correspond au ciphertext
        nonce = exchange_content[:12]
        tag = exchange_content[12:28]
        ciphertext = exchange_content[28:]
        
        # Déchiffre le message avec le nonce et le tag
        plaindata = security.aes_decrypt(ciphertext, aes_key, (nonce,tag))
        
        # Vérification du type de message reçu (MESSAGE, STATEMENT ou EVENT)
        if exchange_type == exchange.ExchangeType.MESSAGE:
            # Parse du message (JSON → dictionnaire Python)
            parsed_msg = message.parse_message(plaindata)
            # Sauvegarde en base de données du message en fonction du destinataire (CHANNEL ou USER)
            if parsed_msg["recipient"]["type"] == "CHANNEL" :
                # Vérifie que le channel existe avant de sauvegarder le message et si j'en suis toujours bien membre
                if not data.channel_exists(parsed_msg["recipient"]["id"]):
                    logger_server.warning(f"Tentative d'envoi de message échouée : le channel {parsed_msg['recipient']['id']} n'existe pas/plus")
                    continue
                elif not data.user_exists_in_channel(clients_connectes[addr]["id"], parsed_msg["recipient"]["id"]):
                    logger_server.warning(f"Tentative d'envoi de message échouée : l'utilisateur {pseudo} n'est pas/plus membre du channel {parsed_msg['recipient']['id']}")
                    continue
                data.add_channel_message(parsed_msg)
                
            elif parsed_msg["recipient"]["type"] == "USER" :
                data.add_private_message(parsed_msg)
            # Update la dernière activité de l'utilisateur
            data.update_user_last_activity(clients_connectes[addr]["id"])
            # Appel de la fonction pour renvoyer le message à tous les clients
            send_msg_to_clients(parsed_msg, exchange_type, clients_connectes)
            
        elif exchange_type == exchange.ExchangeType.STATEMENT:
            # Parse de l'instruction (JSON → dictionnaire Python)
            parsed_statement = statement.parse_statement(plaindata)
            
            # Vérification du type précis de l'instruction
            if parsed_statement["payload"]["name"] == "GET_USERS":
                # Le serveur envoie à l'émetteur un événement USER_UPDATED pour chaque client connecté dans le dictionnaire
                for addr_loop, client_data_loop in clients_connectes.items():
                    
                    pseudo_loop = client_data_loop["pseudo"]
                    public_key_loop = client_data_loop["public_key"]
                    id_loop = client_data_loop["id"]

                    event_payload = event.build_user_updated(time.time(), id_loop, pseudo_loop, True, public_key_loop)
                    
                    # Envoi au client connecté actuel (qui a fait le GET_USERS)
                    single_client = { addr: { "sock": sock_client, "aes_key": aes_key }}
                    send_msg_to_clients(event_payload, exchange.ExchangeType.EVENT, single_client)

            if parsed_statement["payload"]["name"] == "UPDATE_USER":
                # Vérifie le status dans parsed_statement (True = connecté, False = déconnecté)
                # et met à jour le dictionnaire des clients connectés en conséquence
                
                # Récupère le pseudo du client qui a envoyé l'instruction UPDATE_USER depuis le dictionnaire des clients connectés grâce à son adresse (addr)
                pseudo = clients_connectes[addr]["pseudo"]
                user_id = clients_connectes[addr]["id"]
                public_key = clients_connectes[addr]["public_key"]

                # Ajoute le client au dictionnaire des clients connectés si status = True
                if parsed_statement["payload"]["data"]["status"] == True:
                    with clients_lock:
                        clients_connectes[addr] = {
                            "sock": sock_client,
                            "aes_key": aes_key,
                            "pseudo": pseudo,
                            "id": user_id,
                            "public_key": public_key
                        }
                # Supprime le client du dictionnaire des clients connectés si status = False
                elif parsed_statement["payload"]["data"]["status"] == False:
                    with clients_lock:
                        del clients_connectes[addr]
                
                # Renvoie à tous les clients un événement USER_UPDATED avec le pseudo et le status du client qui vient de se connecter ou de se déconnecter
                event_payload = event.build_user_updated(parsed_statement["timestamp"], user_id, pseudo, parsed_statement["payload"]["data"]["status"], public_key)
                send_msg_to_clients(event_payload, exchange.ExchangeType.EVENT, clients_connectes)

            if parsed_statement["payload"]["name"] == "CREATE_CHANNEL":
                # Récupère l'id du client qui a envoyé l'instruction CREATE_CHANNEL depuis le dictionnaire des clients connectés grâce à son adresse (addr)
                owner_id = clients_connectes[addr]["id"]
                timestamp = parsed_statement["timestamp"]
                channel_name = parsed_statement["payload"]["data"]["name"]
                
                # Vérifie que le channel n'existe pas déjà
                if data.channel_exists(channel_name):
                    logger_server.warning(f"Tentative de création de channel échouée : le channel {channel_name} existe déjà")
                    continue 
                
                # Crée le channel en base de données
                channel_id, channel_private_key, channel_public_key = data.add_channel(parsed_statement, owner_id)
                # Ajoute le créateur du channel comme membre du channel en base de données
                data.add_user_to_channel(owner_id, channel_id)
                # Stocke le channel dans le dictionnaire des channels existants
                channels[channel_name] = {
                    "id": channel_id,
                    "private_key": channel_private_key,
                    "public_key": channel_public_key
                }
                # Envoi au client qui a créé le channel un événement CHANNEL_CREATED (avec clé privée du channel)
                event_payload_owner = event.build_channel_created(timestamp, channel_id, channel_name, channel_public_key, channel_private_key)
                single_client = { addr: clients_connectes[addr]}
                send_msg_to_clients(event_payload_owner, exchange.ExchangeType.EVENT, single_client)
                # Envoi à tous les autres clients d'un événement CHANNEL_CREATED (sans clé privée du channel)
                event_payload_others = event.build_channel_created(timestamp, channel_id, channel_name, channel_public_key)
                other_clients = { k: v for k, v in clients_connectes.items() if k != addr } # Dictionnaire des autres clients que celui qui a créé le channel
                send_msg_to_clients(event_payload_others, exchange.ExchangeType.EVENT, other_clients)

            if parsed_statement["payload"]["name"] == "JOIN_CHANNEL":
                
                # Récupère le nom du channel et les infos de l'expéditeur
                channel_name = parsed_statement["payload"]["data"]["name"]
                user_id = clients_connectes[addr]["id"]
                user_pseudo = clients_connectes[addr]["pseudo"]
                # Vérifie que le channel existe
                if not data.channel_exists(channel_name):
                    logger_server.warning(f"Tentative de rejoindre un channel échouée : le channel {channel_name} n'existe pas/plus")
                    continue
                # Récupère l'id du channel
                channel_id = channels[channel_name]["id"]
                is_member = data.user_exists_in_channel(user_id, channel_id)
                
                # Vérifie si on a un champ "secret" dans les données de l'instruction
                if "secret" in parsed_statement["payload"]["data"]:
                    secret = parsed_statement["payload"]["data"]["secret"]
                    
                # Vérifie si l'utilisateur est déjà membre du channel
                if is_member or data.verify_channel_secret(channel_id, secret):
                    # Si déjà membre, construit CHANNEL_JOINED sans clé privée, sinon rajoute la clé + ajoute en db comme membre du channel
                    if is_member:
                        event_payload = event.build_channel_joined(parsed_statement["timestamp"], channel_id, channel_name, channels[channel_name]["public_key"])
                    else:
                        event_payload = event.build_channel_joined(parsed_statement["timestamp"], channel_id, channel_name, channels[channel_name]["public_key"], channels[channel_name]["private_key"])
                        data.add_user_to_channel(user_id, channel_id)
                    # Envoi de l'énévement CHANNEL_JOINED
                    send_msg_to_clients(event_payload, exchange.ExchangeType.EVENT, {addr: clients_connectes[addr]})
                else:
                    logger_server.warning(f"Tentative de rejoindre un channel échouée : secret incorrect pour le channel {channel_name}")
                    continue
            
            # Récupérer les 20 derniers messages privés concernant l'utilisteur
            # + les 20 derniers messages du channel si "name" pas vide
            if parsed_statement["payload"]["name"] == "GET_LAST_MESSAGES":
                
                last_messages = []
                number = parsed_statement["payload"]["data"]["number"]
                pseudo = clients_connectes[addr]["pseudo"]
                
                # Vérifie si le nom du channel est présent dans les données de l'instruction
                if "channel_name" in parsed_statement["payload"]["data"]:
                    channel_name = parsed_statement["payload"]["data"]["channel_name"]
                    
                    # Vérifie que le channel existe
                    if data.channel_exists(channel_name):
                        # S'il existe, récupère l'id du channel
                        channel_id = channels[channel_name]["id"]
                        # Vérifie que l'utilisateur est membre du channel,
                        # si oui récupère les messages dans une variable
                        if data.user_exists_in_channel(clients_connectes[addr]["id"], channel_id):
                            logger_server.info(f"Récupération des messages du channel {channel_name} pour {pseudo}")
                            # Récupère les {number} derniers messages du channel
                            last_messages = data.get_last_channel_message(channel_id, number)
                        else:
                            logger_server.warning(f"Tentative de récupération des messages échouée : l'utilisateur {pseudo} n'est pas/plus membre du channel {channel_name}")
                    else:
                        logger_server.warning(f"Tentative de récupération des messages échouée : le channel {channel_name} n'existe pas/plus")
                
                # Récupère les {number} derniers messages privés concernant l'utilisateur
                last_messages += data.get_last_private_messages(clients_connectes[addr]["id"], number) # FONCTION A FAIRE PLUS TARD
                # Trie les messages par timestamp pour afficher les plus récents en dernier
                last_messages.sort(key=lambda x: x[1]) # Car x[1] = timestamp dans la structure des tuples retournés par get_last_channel_message
                
                # Envoie ces messages au client
                for msg_data in last_messages:
                    # Récupère les infos destinataire et expéditeur pour construire le message
                    recipient_type = msg_data[-1]
                    if recipient_type == "CHANNEL":
                        recipient_name = data.get_channel_name(msg_data[3])
                    elif recipient_type == "USER":
                        recipient_name = data.get_username(msg_data[3])
                    sender_name = data.get_username(msg_data[2])
                    msg_payload = message.build_message(msg_data, sender_name, recipient_name, recipient_type)
                    # Envoi du message au client
                    single_client = { addr: clients_connectes[addr]}
                    send_msg_to_clients(msg_payload, exchange.ExchangeType.MESSAGE, single_client)
                    
    # ------------------------------------------------------------
    # DECONNEXION DU CLIENT
    # ------------------------------------------------------------
    # Déconnexion du client, on sort de la boucle et on ferme le socket
    with clients_lock:
        del clients_connectes[addr]
    sock_client.close()
    logger_server.info(f"Client {addr} deconnecte, attente d'une nouvelle connexion...")


def main():

    connection = database.connect_to_db(DB_PATH) # Ouvre la connexion à la BD
    database.execute_seed(connection) # Crée la BD
    database.close_connection(connection) # Fermer la connexion
    
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

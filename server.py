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
# Verrou qui protègera clients_connectes
clients_lock = Lock()


def broadcast_to_clients(plaindata: dict, exchange_type: exchange.ExchangeType):
    """
    Fonction pour renvoyer un message à tous les clients connectés. Le message est d'abord converti en JSON puis en bytes avant d'être chiffré et envoyé.
    :param plaindata: le message en clair à renvoyer aux clients (dictionnaire Python)
    :param exchange_type: le type d'échange du message
    """
    try:
    # On utilise with comme ça le verrou se libère automatiquement à la fin du bloc, même en cas d'erreur (remplace le acquire et release)
        with clients_lock: 
            # .items() permet de récupérer d'un coup l'adresse (clé) et le socket (valeur) de chaque client ainsi que leur clé AES associée
            for addr, (client_sock, client_key, pseudo) in clients_connectes.items():

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
        logger_server.error(f"Erreur lors du broadcast du message aux clients: {e}", exc_info=True)

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
    
    public_key = network.receive_message(sock_client)
    
    # Vérification de l'existence de l'utilisateur et du mot de passe
    if not data.user_exists(pseudo):
        hashed_password = security.argon2_hash_password(password)
        data.create_user(pseudo, hashed_password, public_key.decode('utf-8'))
        logger_server.info(f"Nouvel utilisateur créé : {pseudo}")
    else:
        user = data.get_user(pseudo)
        verif_mdp = user[2] # Car user = (id, name, secret, created_at, last_activity_at)
        if not security.argon2_verify_password(password, verif_mdp): # Fonction retourne True/False
            logger_server.warning(f"Tentative de connexion échouée pour : {pseudo}")
            sock_client.close()
            return # Permet de ne pas rentrer dans la boucle suivante si le client n'a pas rentré le bon mdp
        logger_server.info(f"Utilisateur authentifié : {pseudo}")

    # ------------------------------------------------------------
    # GESTION CLE RSA
    # ------------------------------------------------------------
     
    
    # ------------------------------------------------------------
    # AJOUT DU CLIENT AU DICTIONNAIRE DES CLIENTS CONNECTES + ENVOI D'UN EVENEMENT DE CONNEXION A TOUS LES CLIENTS
    # ------------------------------------------------------------
    with clients_lock: # Section critique protégée
        # Ajout du client, de sa clé AES et de son pseudo dans le dictionnaire des clients connectés (contiendra des sockets + clés AES)
        clients_connectes[addr] = (sock_client, aes_key, pseudo) # sock_client = connexion faite grâce à addr (ip, port), aes_key = clé de chiffrement symétrique partagée entre le serveur et ce client
    
    # Envoi à tous les clients d'un événement USER_UPDATED avec le pseudo et le status du client qui vient de se connecter
    event_payload = event.build_user_updated(time.time(), pseudo, pseudo, True)
    broadcast_to_clients(event_payload, exchange.ExchangeType.EVENT)

    # ------------------------------------------------------------
    # GESTION DES MESSAGES RECUS
    # (RECEPTION, DECHIFFREMENT, RECHIFFREMENT, RENVOI)
    # ------------------------------------------------------------
    while True:
        response = network.receive_message(sock_client)
        
        # Client déconnecté
        if not response:
            logger_server.info(f"{pseudo} déconnecté brutalement")
            event_payload = event.build_user_updated(time.time(), pseudo, pseudo, False)
            broadcast_to_clients(event_payload, exchange.ExchangeType.EVENT)
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
            # Récupération du user en database
            user = data.get_user(parsed_msg["sender"]["name"])
            # Ajout de l'id du sender dans le message parsé
            parsed_msg["sender"]["id"] = user[0]
            # Sauvegarde en base de données du message
            data.add_message(parsed_msg)
            # Update la dernière activité de l'utilisateur
            data.update_user_last_activity(user[0])
            # Appel de la fonction pour renvoyer le message à tous les clients
            broadcast_to_clients(parsed_msg, exchange_type)
            
        elif exchange_type == exchange.ExchangeType.STATEMENT:
            # Parse de l'instruction (JSON → dictionnaire Python)
            parsed_statement = statement.parse_statement(plaindata)
            
            # Vérification du type précis de l'instruction
            if parsed_statement["payload"]["name"] == "GET_USERS":
                # Le serveur envoie à l'émetteur un événement USER_UPDATED pour chaque client connecté dans le dictionnaire
                with clients_lock:
                    for addr, (client_sock, client_key, pseudo) in clients_connectes.items():

                        user = data.get_user(pseudo)
                        public_key = user[3] # Car user = (id, name, secret, public_key, created_at, last_activity_at)
                        event_payload = event.build_user_updated(time.time(), pseudo, pseudo, True, public_key)
                        # Chiffrement de l'événement avec la clé AES du client
                        nonce, cyphertext, tag = security.aes_encrypt(json.dumps(event_payload).encode('utf-8'), aes_key)
                        payload_renvoi = nonce + tag + cyphertext
                         # Ajout du type du message
                        type_byte = str(exchange.ExchangeType.EVENT.value).encode() # Convertit le type d'échange en byte pour l'inclure dans le message envoyé
                        final_payload = type_byte + payload_renvoi
                        # Envoi de l'événement à l'émetteur de la requête GET_USERS (et pas à tous les clients)
                        network.send_message(sock_client, final_payload)

            if parsed_statement["payload"]["name"] == "UPDATE_USER":
                # Vérifie le status dans parsed_statement (True = connecté, False = déconnecté)
                # et met à jour le dictionnaire des clients connectés en conséquence
                
                # Récupère le pseudo du client qui a envoyé l'instruction UPDATE_USER depuis le dictionnaire des clients connectés grâce à son adresse (addr)
                pseudo = clients_connectes[addr][2] 

                # Ajoute le client au dictionnaire des clients connectés si status = True
                if parsed_statement["payload"]["data"]["status"] == True:
                    with clients_lock:
                        clients_connectes[addr] = (sock_client, aes_key, pseudo)
                # Supprime le client du dictionnaire des clients connectés si status = False
                elif parsed_statement["payload"]["data"]["status"] == False:
                    with clients_lock:
                        del clients_connectes[addr]
                
                # Renvoie à tous les clients un événement USER_UPDATED avec le pseudo et le status du client qui vient de se connecter ou de se déconnecter
                event_payload = event.build_user_updated(parsed_statement["timestamp"], pseudo, pseudo, parsed_statement["payload"]["data"]["status"])
                broadcast_to_clients(event_payload, exchange.ExchangeType.EVENT)

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

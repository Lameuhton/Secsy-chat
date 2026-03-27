from common import network
from common import database
from common import data
from common import security
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


def gerer_client(sock_client, addr): # Arguments générés dans le try

    # Générer les paramètres de la clé publique
    # Envoi de p et g au client
    p, g = security.diffie_hellman_generate_public_parameters(2048)
    network.send_message(sock_client, p.to_bytes(256, byteorder='big')) # 2048 bits // 8 = 256 bytes
    network.send_message(sock_client, g.to_bytes(8, byteorder='big')) # Presque tjrs 2 ou 5 donc 8 bytes

    # Générer les clés et envoyer au client la publique
    private_key = security.diffie_hellman_generate_private_key(p)
    public_key = security.diffie_hellman_compute_public_key(private_key, p, g)
    network.send_message(sock_client, public_key.to_bytes(256, byteorder='big')) # Car send message envoie en bytes

    # Recevoir clé publ du client et calculer clé partagée + clé AES
    peer_public_key = int.from_bytes(network.receive_message(sock_client), byteorder='big') # Clé publique du client != clé publ du serveur
    shared_secret = security.diffie_hellman_compute_shared_secret(private_key, peer_public_key, p)
    aes_key = security.diffie_hellman_derive_shared_key(shared_secret, 32)  # 32 bytes = 256 bits
    
    # Premier message = authentification (avant la boucle)
    premier_message = network.receive_message_as_str(sock_client)
    pseudo, password = premier_message.split("|") # Car on l'a mis en forme <pseudo>|<paswd>
    if not data.user_exists(pseudo):
        hashed_password = security.argon2_hash_password(password)
        data.create_user(pseudo, hashed_password)
        logger_server.info(f"Nouvel utilisateur créé : {pseudo}")
    else:
        user = data.get_user(pseudo)
        verif_mdp = user[2] # Car user = (id, name, secret, created_at, last_activity_at)
        if not security.argon2_verify_password(password, verif_mdp): # Fonction retourne True/False
            logger_server.warning(f"Tentative de connexion échouée pour : {pseudo}")
            sock_client.close()
            return # Permet de ne pas rentrer dans la boucle suivante si le client n'a pas rentré le bon mdp
        logger_server.info(f"Utilisateur authentifié : {pseudo}")

    with clients_lock: # Section critique protégée
        # Ajout du client dans le dictionnaire des clients connectés (contiendra des sockets)
        clients_connectes[addr] = (sock_client, aes_key) # sock_client = connexion faite grâce à addr (ip, port), aes_key = clé de chiffrement symétrique partagée entre le serveur et ce client
    
    # Connexion avec client
    while True:
        message = network.receive_message(sock_client)
        
        if not message: # Client déconnecté
            break
        
        # Déchiffre le message reçu
        # Récupère le nonce, tage et ciphertext (notre message chiffré)
        nonce = message[:12]
        tag = message[12:28]
        ciphertext = message[28:]
        
        # Déchiffre le message avec le nonce et le tag
        plaindata = security.aes_decrypt(ciphertext, aes_key, (nonce,tag))
        
        logger_server.info(f"Serveur: Message reçu de {pseudo} ({addr}) : {plaindata.decode('utf-8')}")
        
        # On utilise with comme ça le verrou se libère automatiquement à la fin du bloc, même en cas d'erreur (remplace le acquire et release)
        with clients_lock: 
            # .items() permet de récupérer d'un coup l'adresse (clé) et le socket (valeur) de chaque client ainsi que leur clé AES associée
            for addr, (client_sock, client_key) in clients_connectes.items():

                # Rechiffre le message avec la clé AES de chaque client
                nonce, cyphertext, tag = security.aes_encrypt(plaindata, client_key)
                # Préparation du payload
                payload = nonce + tag + cyphertext

                # Renvoi du payload au(x) client(x) (en byte car le payload est en byte)
                network.send_message(client_sock, payload)

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

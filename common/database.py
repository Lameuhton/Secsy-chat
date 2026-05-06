from sqlite3 import Connection, connect
from typing import List, Tuple
import os

def connect_to_db(path: str) -> Connection:
    """
    Se connecte à une base de données SQLite et retourne la connection créée
    :param path: le chemin vers la base de données SQLite
    :return: la connection à la base de données
    """
    #NB: SQLite est une base de donnée stockée dans un simple fichier sur le disque
    return connect(path)

def close_connection(connection: Connection):
    """
    Ferme la connexion à la base de données
    :param connection: la connexion à fermer
    """
    connection.close()
    #La fonction ne demande aucun return du coup pas de return

def insert_data(connection: Connection, table: str, columns: Tuple, data: Tuple):
    """
    Insère un tuple au sein d'une table en renseignant les valeurs (data) des colonnes et en utilisant une connexion existante
    :param connection: la connexion existante à la base de données
    :param table: la table dans laquelle insérer les données
    :param columns: le nom des colonnes pour lesquelles des données sont insérées
    :param data: la valeur des colonnes à insérer
    """
    #transformer le tuple columns en tuple str
    colonnes = ", ".join(columns)
    # Crée un message "safe" à placer devant le message à insérer dans SQL pour éviter les injections qui sera remplacé par les data
    secu_injection = ", ".join(["?"] * len(data))
    cursor = connection.cursor() # Crée un curseur (analogie du bibliothécaire)
    # le ligne pourrait ressembler à: cursor.execute("INSERT INTO {table} ({colonnes}) VALUES ({data})") mais peut être vulnérable aux injections sql (msg d'un utilisateur "DROP TABLE")
    # du coup on mes data en valeurs à substituer
    # (f" car il y a des variables dedans
    cursor.execute(f"INSERT INTO {table} ({colonnes}) VALUES ({secu_injection})", data) # Entre accolades pour dire que ce sont des arguments importés de python
    #commit = ctrl+S
    connection.commit()

def select_data(connection: Connection, query: str) -> List[Tuple]: 
    # NB: serait + sécurisé de mettre 'params' qui prendait les paramètres séparés à la requête pour éviter les injections mais
    # paramètres de la fonction inmodifiables car fonction donnée par le prof et consignes interdisent ça.
    """
    Sélectionne des tuples depuis la base de donnée (connection) et retourne les enregistrements correspondants
    :param connection: la connexion déjà établie à la base de données
    :param query: la requête SQL à exécuter sur la base de données (connection)
    :return: les enregistrements correspondants au résultat de la reqête
    """
    cursor = connection.cursor() # Crée un curseur (analogie du bibliothécaire)
    cursor.execute(query) # C'est ici que 'params' aurait pu être introduit '(query, params)'
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    return resultat

def execute_script(connection, path: str):
    """
    Exécute un script directement en base de données en utilisant une connexion existante
    :param connection: la connexion existante à la base de données
    :param path: le chemin vers le fichier contenant le script SQL
    """
    # Vérification de la connexion - Vérifier que :
    # la connection n’est pas None.
    # l’objet possède bien une méthode cursor() qui est indispensable pour exécuter des requêtes.
    # Si erreur --> ValueError
    if connection is None or not hasattr(connection, "cursor"):
        raise ValueError("La connexion fournie est invalide ou fermée.") #Ajouter également dans les logs ?
    # Vérification que le fichier existe bien
    # Si erreur --> FileNotFoundError
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Fichier SQL introuvable : {path}") #Ajouter également dans les logs ?
    # Lecture seule du script SQL
    # Placement du contenu du fichier dans la variable script_content
    # Rappel : le with garantit la fermeture propre du fichier
    with open(path, "r", encoding="utf-8") as file:
        script_content = file.read()
    # Exécution du script
    try:
        #Création du curseur (Pour rappel : il s'agit d'un objet qui permet d'envoyer des requêtes SQL dans la base)
        cursor = connection.cursor()
        #La méthode executescript (possédée ici par sqlite3) est utilisée pour exécuter plusieurs requêtes d’un coup.
        cursor.executescript(script_content)
        #Pour rappel, le commit valide les changements dans la base de données.
        connection.commit()
    #Si une erreur survient :
    except Exception as e:
        # On annule les changements pour éviter de laisser la base dans un état partiel
        # Si erreur --> Exception
        connection.rollback()
        raise Exception(f"Erreur lors de l'exécution du script SQL : {e}") #Ajouter également dans les logs ?
    finally:
        # Fermeture du curseur même si une erreur survient et libère les ressources
        cursor.close()

def execute_seed(connection):
    """
    Si elles n'existent pas, crée les tables, les colonnes et contraintes associées et insère les données nécessaires
    :param connection: la connexion existante à la base de données
    """
    cursor = connection.cursor()
    # On crée la table user si elle n'existe pas
    # UNIQUE sur username pour éviter les doublons
    # TEXT plutot que Varchar car SQLite n'a pas de type de données spécifique pour les chaînes de caractères, il utilise TEXT pour stocker les chaînes de caractères de longueur variable
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id VARCHAR(21) PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            secret VARCHAR(255) NOT NULL,
            public_key TEXT(65535) NOT NULL,
            created_at DATETIME NOT NULL,
            last_activity_at DATETIME NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel (
            id VARCHAR(21) PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            secret VARCHAR(255) NOT NULL,
            private_key TEXT(65535) NOT NULL,
            public_key TEXT(65535) NOT NULL,
            created_at DATETIME NOT NULL,
            owner_id VARCHAR(21) NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES user(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_message (
            id VARCHAR(21) PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            sender_id VARCHAR(21) NOT NULL,
            recipient_id VARCHAR(21) NOT NULL,
            payload_cipher_text TEXT(65535) NOT NULL,
            payload_cipher_text_size INTEGER NOT NULL,
            payload_cipher_text_encrypted_key VARCHAR(255) NOT NULL,
            integrity_checksum VARCHAR(255) NOT NULL,
            integrity_signature TEXT(65535) NOT NULL,
            FOREIGN KEY (recipient_id) REFERENCES channel(id),
            FOREIGN KEY (sender_id) REFERENCES user(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_member (
            channel_id VARCHAR(21) NOT NULL, #peut avoir plusieur fois l'id du channel (si plusieur membres)
            user_id VARCHAR(21) NOT NULL, #peut avoir plusieurs fois un nom (si 1 membre dans plsuieurs channels)
            joined_at DATETIME NOT NULL,
            PRIMARY KEY (channel_id, user_id), #seule la combinaison des deux doit être unique
            FOREIGN KEY (channel_id) REFERENCES channel(id),
            FOREIGN KEY (user_id) REFERENCES user(id)
            ON DELETE CASCADE
        )
    """)
    # Plus tard (messages privés)
    # cursor.execute("""
    #     CREATE TABLE IF NOT EXISTS private_message (
    #         id VARCHAR(21) PRIMARY KEY,
    #         timestamp TIMESTAMP NOT NULL,
    #         sender_id VARCHAR(21) NOT NULL,
    #         recipient_id VARCHAR(21) NOT NULL,
    #         payload_cipher_text TEXT(65535) NOT NULL,
    #         payload_cipher_text_size INTEGER NOT NULL,
    #         payload_cipher_text_encrypted_key VARCHAR(255) NOT NULL,
    #         integrity_checksum VARCHAR(255) NOT NULL,
    #         integrity_signature TEXT(65535) NOT NULL,
    #         FOREIGN KEY (recipient_id) REFERENCES user(id),
    #         FOREIGN KEY (sender_id) REFERENCES user(id)
    #     )
    # """)  
    connection.commit()



from sqlite3 import Connection, connect
from typing import List, Tuple


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
    """
    Sélectionne des tuples depuis la base de donnée (connection) et retourne les enregistrements correspondants
    :param connection: la connexion déjà établie à la base de données
    :param query: la requête SQL à exécuter sur la base de données (connection)
    :return: les enregistrements correspondants au résultat de la reqête
    """
    cursor = connection.cursor() # Crée un curseur (analogie du bibliothécaire)
    cursor.execute(query)
    resultat = cursor.fetchall() # Prend les derniers résultats de la dernière requête exécutée
    return resultat

def execute_script(connection, path: str):
    """
    Exécute un script directement en base de données en utilisant une connexion existante
    :param connection: la connexion existante à la base de données
    :param path: le chemin vers le fichier contenant le script SQL
    """

def execute_seed(connection):
    """
    Si elles n'existent pas, crée les tables, les colonnes et contraintes associées et insère les données nécessaires
    :param connection: la connexion existante à la base de données
    """

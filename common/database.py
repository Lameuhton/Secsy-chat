from sqlite3 import Connection
from typing import List, Tuple


def connect_to_db(path: str) -> Connection
    """
    Se connecte à une base de données SQLite et retourne la connection créée
    :param path le chemin vers la base de données SQLite
    :return la connection à la base de données
    """

def close_connection(connection: Connection)
    """
    Ferme la connexion à la base de données
    :param connection la connexion à fermer
    """

def insert_data(connection: Connection, table: str, columns: Tuple, data: Tuple):
    """
    Insère un tuple au sein d'une table en renseignant les valeurs (data) des colonnes et en utilisant une connexion existante
    :param connection la connexion existante à la base de données
    :param table la table dans laquelle insérer les données
    :param columns le nom des colonnes pour lesquelles des données sont insérées
    :param data la valeur des colonnes à insérer
    """


def select_data(connection: Connection, query: str) -> List[Tuple]
    """
    Sélectionne des tuples depuis la base de donnée (connection) et retourne les enregistrements correspondants
    :param connection la connexion déjà établie à la base de données
    :param query la requête SQL à exécuter sur la base de données (connection)
    :return les enregistrements correspondants au résultat de la reqête
    """

def execute_script(connection, path: str):
    """
    Exécute un script directement en base de données en utilisant une connexion existante
    :param connection la connexion existante à la base de données
    :param path le chemin vers le fichier contenant le script SQL
    """

def execute_seed(connection):
    """
    Si elles n'existent pas, crée les tables, les colonnes et contraintes associées et insère les données nécessaires
    :param connection la connexion existante à la base de données
    """

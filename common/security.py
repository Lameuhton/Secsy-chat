from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import dh
import secrets

def argon2_hash_password(plain_password: str) -> str:
    """
    Hache un mot de passe à l'aide Argon2
    :param plain_password le mot de passe en clair à hacher
    :return le mot de passe haché
    """


def argon2_verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair est identique à sa version hashée à l'aide d'Argon2
    :param plain_password le mot de passe en clair à comparer
    :param hashed_password le mot de passe haché à comparer
    :return `True` si les mots de passe sont identiques, sinon `False`
    """


def generate_encryption_key(size: int = 256) -> bytes:
    """
    Génère une clé de chiffrement d'une taille donnée (size)
    :param size la taille de la clé en bits à générer
    :return la clé de chiffrement générée en bytes
    """


def aes_encrypt(plain_data: bytes, key: bytes) -> Tuple:
    """
    Chiffre des données à l'aide d'AES-GCM
    :param plain_data les données en clair à chiffrer
    :param key la clé de chiffrement
    :return le tuple contenant les éléments nécessaires au déchiffrement (nonce, header, ciphertext, tag)
    """


def aes_decrypt(encrypted_data: bytes, key: bytes, decryption_data: Tuple) -> bytes:
    """
    Déchiffre des données à l'aide d'AES GCM
    :param encrypted_data les données à déchiffrer
    :param key la clé de déchiffrement
    :param decryption_data le tuple contenant les éléments nécessaires au déchiffrement (nonce, header, tag)
    :return les données déchiffrées (en clair)
    """


def diffie_hellman_generate_public_parameters(bits: int) -> Tuple[int, int]:
    """
    Génère les paramètres publics Diffie-Hellman.

    :param bits la taille du nombre premier sûr (safe prime) p en bits.
    :return (p, g)
        p le nombre premier
        g le générateur du sous-groupe
    """
    #Lors de l'appel de la fonction - Préciser le nombre de bits : 2048 = taille de la clé
    #A signaler aux filles - import secrets - Ajouté dans la version 3.6. de Python
    #La fonction dh.generate_parameters génère un grand nombre premier p et lui associe un générateur g (souvent 2 ou 5)
    parameters = dh.generate_parameters(generator=2, key_size=bits)
    numbers = parameters.parameter_numbers()
    #La fonction parameter_numbers renvoit un objet objet DHParameterNumbers. 
    #On doit extraire les paramètres p et g pour retourner un tuple de int comme attendu.
    return (numbers.p, numbers.g)


def diffie_hellman_generate_private_key(p: int) -> int:
    """
    Génère une clé privée aléatoire pour Diffie-Hellman dans [2, p-2].

    :param p le nombre premier sûr (safe prime)
    :return la clé privée générée sur base du nombre premier
    """
    #On évite 0 et 1 pour avoir une généraration de nombre aléatoire plus sûre.
    private_key = secrets.randbelow(p - 2) + 2
    return private_key


def diffie_hellman_compute_public_key(private_key: int, p: int, g: int) -> int:
    """
    Calcule la clé publique `g^a mod p`.

    :param private_key Clé privée a
    :param p le nombre premier sûr (safe prime)
    :param g le générateur du sous-groupe
    :return la clé publique A
    """
    # La fonction intégrée pow(base, exposant, modulo) est optimisée pour la génération de clés.
    # De plus, elle évite les dépassements de mémoire.
    public_key = pow(g, private_key, p)
    return public_key

def diffie_hellman_compute_shared_secret(private_key: int, peer_public_key: int, p: int) -> int:
    """
    Calcule le secret partagé (`B^a mod p`)

    :param private_key la Clé privée locale a
    :param peer_public_key la clé publique reçue B
    :param p Le nombre premier sûr (safe prime)
    :return le secret partagé
    """
    shared_secret = pow(private_key, peer_public_key, p)
    return shared_secret


def diffie_hellman_derive_shared_key(shared_secret: int, key_length: int) -> bytes:
    """
    Dérive une clé symétrique à partir du secret partagé

    :param shared_secret le secret Diffie-Hellman brut
    :param key_length la longueur désirée en bytes
    :return la clé symétrique prête à l'emploi
    """

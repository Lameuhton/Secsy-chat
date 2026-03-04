from typing import Tuple
from argon2 import PasswordHasher
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Initialisation du passwordhasher
ph = PasswordHasher()

def argon2_hash_password(plain_password: str) -> str:
    """
    Hache un mot de passe à l'aide Argon2
    :param plain_password le mot de passe en clair à hacher
    :return le mot de passe haché
    """
    return ph.hash(plain_password)


def argon2_verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair est identique à sa version hashée à l'aide d'Argon2
    :param plain_password le mot de passe en clair à comparer
    :param hashed_password le mot de passe haché à comparer
    :return `True` si les mots de passe sont identiques, sinon `False`
    """
    try:
        # Retournera True si la vérification entre les deux correspond
        return ph.verify(hashed_password,plain_password)
    except Exception:
        # Si le hash est invalide ou ne correspond pas, lève une erreur et renvoie false
        return False

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

def diffie_hellman_generate_private_key(p: int) -> int:
    """
    Génère une clé privée aléatoire pour Diffie-Hellman dans [2, p-2].

    :param p le nombre premier sûr (safe prime)
    :return la clé privée générée sur base du nombre premier
    """


def diffie_hellman_compute_public_key(private_key: int, p: int, g: int) -> int:
    """
    Calcule la clé publique `g^a mod p`.

    :param private_key Clé privée a
    :param p le nombre premier sûr (safe prime)
    :param g le générateur du sous-groupe
    :return la clé publique A
    """


def diffie_hellman_compute_shared_secret(
    private_key: int, peer_public_key: int, p: int
) -> int:
    """
    Calcule le secret partagé (`B^a mod p`)

    :param private_key la Clé privée locale a
    :param peer_public_key la clé publique reçue B
    :param p Le nombre premier sûr (safe prime)
    :return le secret partagé
    """


def diffie_hellman_derive_shared_key(shared_secret: int, key_length: int) -> bytes:
    """
    Dérive une clé symétrique à partir du secret partagé

    :param shared_secret le secret Diffie-Hellman brut
    :param key_length la longueur désirée en bytes
    :return la clé symétrique prête à l'emploi
    """
    # On transforme l'int en bytes (format "big-endian" car shared_secret est un int géant)
    # On calcule la taille nécessaire pour que le secret rentre dans la variable
    secret_bytes = shared_secret.to_bytes((shared_secret.bit_length() + 7) // 8, byteorder='big')
    
    # On utilise HKDF pour mélanger le secret avec une fonction de hachage (SHA256) pour qu'il devienne parfaitement aléatoire visuellement
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=None, 
        info=b'handshake data', #Optionnel, sert à lier la clé à un contexte
    )
    
    return hkdf.derive(secret_bytes)
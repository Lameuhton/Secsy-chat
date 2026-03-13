from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import dh
import secrets
from Crypto.Cipher import AES
import os
from argon2 import PasswordHasher
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Initialisation du passwordhasher
ph = PasswordHasher()

def argon2_hash_password(plain_password: str) -> str:
    """
    Hache un mot de passe à l'aide Argon2       # Argon2 car lauréat du Password Hashing Compétition
    :param plain_password: le mot de passe en clair à hacher
    :return: le mot de passe haché
    """
    return ph.hash(plain_password)


def argon2_verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair est identique à sa version hashée à l'aide d'Argon2
    :param plain_password: le mot de passe en clair à comparer
    :param hashed_password: le mot de passe haché à comparer
    :return: `True` si les mots de passe sont identiques, sinon `False`
    """
    try:
        # Retournera True si la vérification entre les deux correspond, ne peut renvoyer que True ou une erreur
        return ph.verify(hashed_password,plain_password)
    except Exception:
        # Si le hash est invalide ou ne correspond pas, lève une erreur et renvoie false
        return False

def generate_encryption_key(size: int = 256) -> bytes:
    """
    Génère une clé de chiffrement d'une taille donnée (size)
    :param size: la taille de la clé en bits à générer # bits/8 = bytes -> 32 octets (bytes)
    :return: la clé de chiffrement générée en bytes
    """
    size_bytes = size//8
    # génère size_bytes bytes aléatoires
    # Ne pas utiliser random.randint car peut être tronqué et prévisible, os car se base sur les bytes des données récoltées par l'os (temp du process, mvmt souris, frappe clavier)
    return os.urandom(size_bytes) 


def aes_encrypt(plain_data: bytes, key: bytes) -> Tuple:
    """
    Chiffre des données à l'aide d'AES-GCM          #Chiffrement symétrique, même clef pour chiffrer que déchiffrer       #AES-GCM car rapide et fiable (moins d'erreur)
    :param plain_data: les données en clair à chiffrer
    :param key: la clé de chiffrement
    :return: le tuple contenant les éléments nécessaires au déchiffrement (nonce, header, ciphertext, tag)
    """
    # nonce : recommandé à 96 bits, nombre aléatoire à usage unique, évite la détection de patterns --> comme le salt mais n'est jamais le même
    # header : métadonnées en clair, vérifiées mais non chiffrées lors du déchiffrement
    # ciphertext : les données chiffrées
    # tag : signature d'intégrité, permet de détecter toute modification du message
    nonce=os.urandom(12)
    
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!# 
    header= b"header" #b = "ceci est des bytes et non du texte"
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#

    cadenas_cipher = AES.new(key, AES.MODE_GCM, nonce=nonce) # Prépare l'objet avec sa clé et le nonce, comme préparer un cadenas avec sa combinaison.
    # AES.MODE_GCM : le mode GCM
    cadenas_cipher.update(header)
    # chiffrer les données ET générer le tag
    ciphertext, tag = cadenas_cipher.encrypt_and_digest(plain_data)
    return (nonce, header, ciphertext, tag)

def aes_decrypt(encrypted_data: bytes, key: bytes, decryption_data: Tuple) -> bytes:
    """
    Déchiffre des données à l'aide d'AES GCM
    :param encrypted_data: les données à déchiffrer
    :param key: la clé de déchiffrement
    :param decryption_data: le tuple contenant les éléments nécessaires au déchiffrement (nonce, header, tag)
    :return: les données déchiffrées (en clair)
    """
    # Extraire nonce, header et tag (ciphertext n'étant pas dans le tuple decryption_data)
    nonce, header, tag = decryption_data
    cadenas_cipher = AES.new (key, AES.MODE_GCM, nonce=nonce) # Prépare l'objet grâce à sa clé et le nonce, comme préparer un cadenas avec sa combinaison.
    # AES.MODE_GCM : le mode GCM
    cadenas_cipher.update(header)
    try:
        plain_data = cadenas_cipher.decrypt_and_verify(encrypted_data, tag) #NB: la clé est déjà dans le cadenas_cipher, ici vérifie le tag mais ne le retourne pas.
        return plain_data
    except ValueError:
        print("Erreur : les données ont été altérées (tag non correspondant au message donné).")

def diffie_hellman_generate_public_parameters(bits: int) -> Tuple[int, int]:
    """
    Génère les paramètres publics Diffie-Hellman.   # p et g
    # Avantages : sécurité accrue basé sur des mathématiques complexes (sécurtié des clés et des communications)
    # Même si la communication est interceptée elle ne peut être décryptée.
    :param bits: la taille du nombre premier sûr (safe prime) p en bits.
    :return: (p, g)
        p le nombre premier
        g le générateur du sous-groupe
    """
    #Lors de l'appel de la fonction - Préciser le nombre de bits : 2048 = taille de la clé
    #La fonction dh.generate_parameters génère un grand nombre premier p et lui associe un générateur g (souvent 2 ou 5)
    parameters = dh.generate_parameters(generator=2, key_size=bits)
    numbers = parameters.parameter_numbers()
    #La fonction parameter_numbers extrait les valeurs p et g dans un objet accessible. 
    #On doit extraire les paramètres p et g pour retourner un tuple de int comme attendu.
    p = numbers.p # number.p est une propirété de l'objet number qui retourne un int
    g = numbers.g # number.g est une propriété de l'objet number qui retourne un int
    return (p, g)

def diffie_hellman_generate_private_key(p: int) -> int:
    """
    Génère une clé privée aléatoire pour Diffie-Hellman dans [2, p-2].

    :param p: le nombre premier sûr (safe prime)
    :return: la clé privée générée sur base du nombre premier
    """
    #On évite 0 et 1 pour avoir une généraration de nombre aléatoire plus sûre 
    #De même pour p et p-1 qui peuvent donner des nombres prévisibles
    private_key = secrets.randbelow(p - 3) + 2 # Génère un nbr de 0 à p-4 inclus et on décale tout de +2 -> 2 à p-2 inclus
    return private_key


def diffie_hellman_compute_public_key(private_key: int, p: int, g: int) -> int:
    """
    Calcule la clé publique `g^a mod p`.

    :param private_key: Clé privée a
    :param p: le nombre premier sûr (safe prime)
    :param g: le générateur du sous-groupe
    :return: la clé publique A
    """
    # La fonction intégrée pow(base, exposant, modulo) est optimisée pour la génération de clés.
    # De plus, elle évite les dépassements de mémoire.
    public_key = pow(g, private_key, p)
    return public_key

def diffie_hellman_compute_shared_secret(private_key: int, peer_public_key: int, p: int) -> int: # "Clé rouge"
    """
    Calcule le secret partagé (`B^a mod p`)

    :param private_key: la Clé privée locale a
    :param peer_public_key: la clé publique reçue B
    :param p: Le nombre premier sûr (safe prime)
    :return: le secret partagé
    """
    shared_secret = pow(peer_public_key, private_key, p)
    return shared_secret


def diffie_hellman_derive_shared_key(shared_secret: int, key_length: int) -> bytes:
    """
    Dérive une clé symétrique à partir du secret partagé

    :param shared_secret: le secret Diffie-Hellman brut
    :param key_length: la longueur désirée en bytes
    :return: la clé symétrique prête à l'emploi
    """
    # On transforme l'int en bytes (format "big-endian" car shared_secret est un int géant)
    # On calcule la taille nécessaire pour que le secret rentre dans la variable
    secret_bytes = shared_secret.to_bytes((shared_secret.bit_length() + 7) // 8, byteorder='big')
    
    # On utilise HKDF pour mélanger le secret avec une fonction de hachage (SHA256) pour qu'il devienne parfaitement aléatoire visuellement
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=None,
    )
    return hkdf.derive(secret_bytes)
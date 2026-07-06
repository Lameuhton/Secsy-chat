# Secsy Chat

Projet réalisé dans le cadre du cours **UE14 – Intégration de la sécurité 1**.

Secsy Chat est une application de messagerie sécurisée permettant à plusieurs utilisateurs de communiquer via des canaux ou des messages privés en utilisant différents mécanismes de sécurité (authentification, chiffrement et intégrité).

## Installation

Installer les dépendances :

```bash
pip install -r requirements.txt
```

## Lancement du serveur

Exécuter :

```bash
python server.py
```

Le serveur écoute par défaut sur le port **4000**.

## Lancement d’un client

Exécuter :

```bash
python client.py <adresse_ip> <port> <pseudonyme>
```

Exemple :

```bash
python client.py 127.0.0.1 4000 Alice
```

Le mot de passe sera demandé au lancement.

Pour lancer plusieurs utilisateurs, ouvrir plusieurs terminaux :

```bash
python client.py 127.0.0.1 4000 Alice
python client.py 127.0.0.1 4000 Bob
python client.py 127.0.0.1 4000 Charlie
```

## Commandes disponibles

Créer un canal :

```bash
/new <nom_du_canal> <mot_de_passe>
```

Rejoindre un canal :

```bash
/join <nom_du_canal> [mot_de_passe]
```

Le mot de passe est requis uniquement lors de la première adhésion au canal.

Quitter un canal :

```bash
/leave <nom_du_canal>
```

Supprimer un canal (uniquement le propriétaire du canal) :

```bash
/delete <nom_du_canal>
```

Expulser un membre (uniquement le propriétaire du canal) :

```bash
/kick <nom_du_canal> <nom_utilisateur>
```

Envoyer un message privé :

```bash
/pm <nom_utilisateur> <message>
```

## Informations complémentaires

* __Lors d’un premier lancement du serveur, l’initialisation de certains mécanismes cryptographiques peut prendre quelques instants (jusqu'à 40 secondes max).__
* Lorsqu’un canal est créé, il n’est pas rejoint automatiquement. Il faut ensuite le rejoindre via `/join`.
* Pour envoyer un message classique dans la TUI, un canal doit être rejoint et sélectionné comme contexte actif.
* Les messages privés peuvent être envoyés à tout moment avec `/pm`.
* Certaines commandes possèdent des paramètres optionnels : si une commande ne produit aucun effet, vérifier sa syntaxe.

En cas de comportement inattendu, il est recommandé de consulter les logs clients qui contiennent généralement les informations les plus utiles concernant les erreurs d’utilisation ou les problèmes liés aux commandes.

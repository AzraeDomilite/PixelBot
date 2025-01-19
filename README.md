# PixelBot

Discord bot pour la gestion des tokens.

## Installation

1. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer le fichier .env avec votre token Discord.

## Démarrage

```bash
make build  # Construire les images
make up     # Démarrer les conteneurs
```

## Tests

```bash
make test   # Lancer les tests
make lint   # Vérifier le code
make format # Formater le code
```

FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Définir les variables d'environnement
ENV PYTHONPATH=/app

# Commande pour démarrer le bot
CMD ["python", "-m", "src.main"]
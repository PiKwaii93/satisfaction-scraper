# Image officielle optimisée pour Playwright
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier des dépendances et installer
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

# COPIER TOUT LE CONTENU DU PROJET
# Cela inclut ton dossier app/ et tes fichiers à la racine
COPY . .

# Variables d'environnement
ENV PYTHONPATH="${PYTHONPATH}:/app"
ENV PYTHONUNBUFFERED=1

CMD ["python", "app/main.py"]

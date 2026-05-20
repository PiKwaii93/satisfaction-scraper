# Rapport Technique : Pipeline de Collecte et Analyse d'Avis Clients

## 1. Introduction & Objectif Métier
* **Objectif :** Automatiser la veille concurrentielle sur Trustpilot pour la marque Showroomprivé afin d'identifier les leviers d'amélioration de la satisfaction client.
* **Problématique :** Comment transformer des données non structurées (avis textuels, dates relatives) en indicateurs quantitatifs (KPIs) exploitables par une équipe marketing ?

## 2. Architecture Technique
* **Stack technologique :**
    * **Orchestration :** Docker & Docker Compose (pour un environnement reproductible).
    * **Collecte :** Playwright (Scraping dynamique).
    * **Stockage :** PostgreSQL (Modélisation en schéma en étoile : `dim_companies`, `fact_reviews`).
    * **Analyse :** Pandas & TextBlob (NLP).

* **Pipeline Data (ETL) :**
    1. **Extraction :** Script Python utilisant Playwright pour extraire les avis.
    2. **Transformation :** Normalisation des dates relatives (ex: "il y a 33 minutes" → format `TIMESTAMP`) et nettoyage des verbatims via Regex.
    3. **Chargement :** Injection sécurisée en base de données avec `psycopg2`.

## 3. Analyse des Résultats
* **Performance du pipeline :** Automatisation complète de l'ingestion, permettant une mise à jour rapide de la base de données.
* **KPIs observés :**
    * **Nombre d'avis analysés :** 80
    * **Note moyenne :** 2.95 / 5
    * **Sentiment moyen (NLP) :** 0.07 (sur une échelle de -1 à 1)

* **Interprétation :** Une note moyenne proche de 3/5 et un sentiment NLP neutre suggèrent que les avis sont majoritairement factuels et pointent des processus opérationnels spécifiques (délais, logistique) plutôt que des expériences purement émotionnelles.

## 4. Défis rencontrés & Solutions
* **Défi 1 : Format des données :** Les dates "relatives" de Trustpilot n'étaient pas directement exploitables par SQL.
    * *Solution :* Développement d'une fonction de parsing Python robuste.
* **Défi 2 : Orchestration Docker :** Communication entre conteneurs.
    * *Solution :* Utilisation des réseaux Docker privés (`satisfaction-scraper_default`) et configuration stricte des variables d'environnement (`DB_HOST`).

## 5. Conclusion & Perspectives
* **Conclusion :** Le système permet de générer un rapport de satisfaction en temps réel sans intervention manuelle, prouvant la robustesse de l'approche conteneurisée.
* **Perspectives :**
    * Déploiement d'un dashboard **Streamlit** pour visualiser l'évolution des sentiments dans le temps.
    * Affinement du modèle NLP pour catégoriser automatiquement les avis par thèmes (Livraison, SAV, Qualité).

*Projet réalisé dans le cadre de la formation DataScientest.*
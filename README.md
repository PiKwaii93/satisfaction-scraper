# Satisfaction Scraper

Pipeline complet de collecte, analyse de sentiment et visualisation d'avis clients Trustpilot.

Le projet scrape des avis, les charge en base PostgreSQL, applique un modèle de classification de sentiment entraîné sur des annotations manuelles, puis expose les résultats dans un dashboard Streamlit.

## Objectif

L'objectif est de construire un modèle propriétaire de classification de sentiment capable d'analyser des avis clients issus de plusieurs entreprises et secteurs, en privilégiant le contenu textuel des avis plutôt que la note seule.

Le modèle prédit trois classes :

- `Positif`
- `Neutre`
- `Négatif`

Le système utilise la note client comme signal auxiliaire, mais le texte reste central. Des garde-fous métier corrigent aussi certains contresens fréquents, par exemple :

- avis 1 ou 2 étoiles prédits positifs ;
- avis explicitement négatifs contenant "je suis déçu", "arnaque", "pas reçu", etc. ;
- avis positifs avec double négation comme "jamais déçue" ;
- avis mixtes où un problème a été résolu efficacement.

## Stack Technique

- Python
- Playwright pour le scraping Trustpilot
- Pandas pour la préparation des données
- scikit-learn pour le modèle ML
- MLflow pour le suivi et le registre du modèle
- PostgreSQL pour le stockage des avis
- Redis + Celery pour les analyses en arriere-plan
- FastAPI pour l'API produit
- React, Vite et TypeScript pour l'interface client
- Streamlit pour le dashboard
- Docker Compose pour l'orchestration locale

## Architecture

```text
satisfaction-scraper/
|-- app/
|   |-- scraper.py                    # Scraping Trustpilot
|   |-- etl.py                        # Chargement des avis en base
|   |-- sentiment_analysis.py         # Prédiction sentiment + garde-fous
|   |-- train_model.py                # Entraînement du modèle supervisé
|   |-- external_trustpilot.py        # Scraping/prédiction d'entreprises externes
|   |-- compare_sentiment_modes.py    # Comparaison texte seul / texte + note
|   |-- dashboard.py                  # Dashboard Streamlit
|   `-- models/
|       `-- sentiment_model.pkl       # Modèle sérialisé local
|-- data/
|   |-- showroom_reviews.json         # Avis source historiques
|   `-- external/                     # Jeux externes de validation
|-- annotations_training.csv          # Corpus d'entraînement consolidé
|-- annotations_manual_labels.csv     # Annotations manuelles initiales
|-- docker-compose.yml
|-- Dockerfile
|-- init_db.sql
`-- requirements.txt
```

## Prérequis

- Docker Desktop
- Docker Compose
- PowerShell ou terminal équivalent

Le projet a été principalement utilisé sous Windows avec la commande `docker-compose`.

## Démarrage Rapide

Depuis la racine du projet :

```powershell
cd C:\Users\Maxen\OneDrive\Documents\GitHub\satisfaction-scraper
```

Construire les images :

```powershell
docker-compose build
```

Démarrer les services principaux :

```powershell
docker-compose up -d postgres_db mlflow redis celery_worker api frontend
```

Accéder aux interfaces :

- Dashboard Streamlit : <http://localhost:8501>
- API FastAPI : <http://localhost:8000/docs>
- MLflow UI : <http://localhost:5000>

## API Produit

Le service `api` pose le socle de la future application client React/Vite. Il historise les analyses au lieu de remplacer les avis affiches dans `fact_reviews`.

Flux cible :

1. l'utilisateur fournit une entreprise ou une URL Trustpilot ;
2. l'API cree un `analysis_run` ;
3. une tache Celery est envoyee dans Redis ;
4. le worker Celery execute le scraping Trustpilot ;
5. le modele de sentiment predit les labels ;
6. les irritants metier sont detectes ;
7. les evenements d'execution sont journalises ;
8. le rapport est consultable par API.

Demarrer l'API avec les autres services :

```powershell
docker-compose up -d postgres_db mlflow redis celery_worker api frontend
```

Documentation interactive :

- API FastAPI : <http://localhost:8000/docs>

Endpoints principaux :

```text
GET    /health
POST   /analysis-runs
POST   /analysis-runs/preview-csv
POST   /analysis-runs/import-csv
GET    /analysis-runs
GET    /analysis-runs/{run_id}
POST   /analysis-runs/{run_id}/execute
GET    /analysis-runs/{run_id}/summary
GET    /analysis-runs/{run_id}/reviews
POST   /analysis-runs/{run_id}/reviews/{review_id}/feedback
DELETE /analysis-runs/{run_id}/reviews/{review_id}/feedback
GET    /analysis-runs/feedback/quality
GET    /analysis-runs/{run_id}/events
GET    /analysis-runs/{run_id}/export
GET    /analysis-runs/{run_id}/feedback/export
```

### Securite API

Les endpoints `/analysis-runs` sont proteges par une API Key transmise dans le header `X-API-Key`.
L'endpoint `/health` reste public pour les sondes de disponibilite.

En local Docker, la cle de developpement est configuree dans `docker-compose.yml` :

```text
dev-satisfaction-key
```

Pour tester un endpoint protege depuis PowerShell :

```powershell
$headers = @{ "X-API-Key" = "dev-satisfaction-key" }
Invoke-RestMethod http://localhost:8000/analysis-runs -Headers $headers
```

En production, il faut remplacer cette valeur par une cle secrete fournie via variable d'environnement `API_KEY`.

Exemple de lancement d'analyse depuis PowerShell :

```powershell
$headers = @{ "X-API-Key" = "dev-satisfaction-key" }
$body = @{
  company = "https://fr.trustpilot.com/review/www.darty.com"
  source = "trustpilot"
  stars = @(1, 2, 3, 4, 5)
  pages_per_star = 1
  execute_immediately = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/analysis-runs -Headers $headers -ContentType "application/json" -Body $body
```

### Import CSV d'avis

L'application peut aussi analyser un fichier CSV fourni par l'utilisateur, sans passer par le scraping Trustpilot. C'est le chemin recommande pour brancher des exports clients, des avis issus d'autres plateformes ou une future integration API.

Avant le lancement, le frontend previsualise le fichier pour afficher les colonnes detectees, le nombre d'avis exploitables, les lignes ignorees et quelques exemples de verbatims. Si l'auto-detection ne correspond pas au fichier fourni, l'utilisateur peut corriger le mapping des colonnes avant de confirmer l'import.

Colonnes acceptees :

- `verbatim` obligatoire, avec alias possibles : `avis`, `review`, `text`, `texte`, `comment`, `commentaire`, `body`, `message` ;
- `rating` optionnel, avec alias possibles : `note`, `stars`, `etoiles`, `score` ;
- `author` optionnel, avec alias possibles : `author_name`, `auteur`, `nom`, `name`, `user`, `client` ;
- `date` optionnel, avec alias possibles : `raw_date`, `review_date`, `created_at`, `published_at` ;
- `company_responded` optionnel, avec alias possibles : `responded`, `response`, `reponse`, `has_response`.

Les runs importes en CSV alimentent le meme rapport entreprise, le meme benchmark, les memes corrections humaines et les memes exports que les runs Trustpilot.

## Frontend React

Le dossier `frontend/` contient la premiere interface client React + Vite + TypeScript.

Elle permet de :

- lancer une nouvelle analyse Trustpilot ;
- previsualiser puis importer un CSV d'avis clients ;
- consulter l'historique des analyses ;
- afficher un rapport entreprise avec KPIs, sentiments et irritants ;
- obtenir une synthese decisionnelle avec priorites, actions recommandees et points de vigilance ;
- piloter la qualite IA avec les corrections humaines disponibles pour le prochain entrainement ;
- suivre le journal d'execution d'une analyse en cours ;
- filtrer les avis par sentiment ;
- corriger manuellement le sentiment d'un avis pour alimenter un futur dataset de reentrainement ;
- exporter un rapport entreprise imprimable en PDF depuis le navigateur ;
- exporter les avis d'un run ou les corrections humaines en CSV.

Demarrer l'application :

```powershell
docker-compose up -d postgres_db mlflow redis celery_worker api frontend
```

Acces local :

- Frontend React : <http://localhost:5173>
- API FastAPI : <http://localhost:8000/docs>

Commandes utiles cote frontend :

```powershell
cd frontend
npm install
npm run build
```

## Pipeline Principal

Pour relancer le pipeline historique complet :

```powershell
docker-compose run --rm worker python /app/app/main.py
docker-compose up -d dashboard
```

Ce pipeline :

1. scrape les avis configurés ;
2. applique la prédiction de sentiment ;
3. charge les résultats dans PostgreSQL ;
4. rend les données visibles dans Streamlit.

## Réentraîner le Modèle

Le fichier d'entraînement principal est :

```text
annotations_training.csv
```

Il contient les colonnes utiles :

- `id`
- `verbatim`
- `rating`
- `manual_label`
- `label_confidence`
- `issue_type`
- `is_mixed`
- `justification_courte`

Pour réentraîner le modèle :

Depuis l'application React, la section **Entrainement IA** permet de lancer un
reentrainement asynchrone via Celery, de suivre son statut, de consulter les
metriques et de voir la version MLflow exposee avec l'alias `production`.

Le reentrainement reste aussi disponible en ligne de commande :

```powershell
docker-compose run --rm worker python /app/app/train_model.py
docker-compose up -d --force-recreate api celery_worker frontend
```

Le script :

- charge `annotations_training.csv` ;
- ajoute automatiquement les corrections humaines stockées dans `review_feedback` si PostgreSQL est disponible ;
- pondère les corrections humaines avec `FEEDBACK_SAMPLE_WEIGHT` (`6.0` par défaut) pour leur donner plus d'influence que les annotations historiques ;
- ignore les verbatims vides pour l'entraînement ;
- écrit un snapshot auditable du dataset combiné dans `data/training/sentiment_training_dataset.csv`, incluant le poids d'entraînement de chaque ligne ;
- effectue un split train/test stratifié ;
- affiche accuracy, precision, recall et F1-score par classe, globalement et par source de dataset ;
- réentraîne un modèle final sur 100 % des verbatims annotés non vides ;
- sérialise le modèle dans `app/models/sentiment_model.pkl` ;
- publie une nouvelle version dans MLflow avec l'alias `production` ;
- resynchronise les prédictions en base.

Les entrainements lances depuis l'interface sont historises dans
`model_training_runs` avec leur statut, duree, accuracy, F1, poids des
corrections, lignes d'entrainement et version MLflow produite.

## Tester une Entreprise Externe

Le script `app/external_trustpilot.py` permet de tester le modèle sur une entreprise Trustpilot différente du corpus d'origine.

Exemple avec Darty :

```powershell
docker-compose run --rm worker python /app/app/external_trustpilot.py --company https://fr.trustpilot.com/review/www.darty.com --pages-per-star 1 --sync-db --replace-db
docker-compose up -d dashboard
```

Options utiles :

- `--company` : URL Trustpilot de l'entreprise.
- `--pages-per-star` : nombre de pages à scraper par note.
- `--stars` : notes ciblées, par exemple `1,2,3,4,5`.
- `--skip-scrape` : réutilise le JSON déjà présent dans `data/external`.
- `--sync-db` : charge les avis dans PostgreSQL.
- `--replace-db` : vide `fact_reviews` avant chargement pour afficher uniquement ce test externe.

Exemple sans re-scraper, en réutilisant le JSON existant :

```powershell
docker-compose run --rm worker python /app/app/external_trustpilot.py --company https://fr.trustpilot.com/review/www.darty.com --pages-per-star 1 --skip-scrape --sync-db --replace-db
docker-compose up -d dashboard
```

## Comparer les Modes de Sentiment

Le script `app/compare_sentiment_modes.py` sert à comparer plusieurs stratégies :

- texte + note ;
- texte + note faiblement pondérée ;
- texte seul.

Commande depuis la base courante :

```powershell
docker-compose run --rm worker python /app/app/compare_sentiment_modes.py --source db
```

Avec une pondération personnalisée de la note :

```powershell
docker-compose run --rm worker python /app/app/compare_sentiment_modes.py --source db --rating-weight 0.1
```

Le résultat est exporté dans :

```text
data/external/sentiment_mode_comparison.csv
```

## Vérifications Utiles

Distribution des sentiments en base :

```powershell
docker-compose exec postgres_db psql -U admin -d satisfaction_client -c "SELECT sentiment_label, COUNT(*) FROM fact_reviews GROUP BY sentiment_label ORDER BY sentiment_label;"
```

Répartition par note et sentiment :

```powershell
docker-compose exec postgres_db psql -U admin -d satisfaction_client -c "SELECT rating, sentiment_label, COUNT(*) FROM fact_reviews GROUP BY rating, sentiment_label ORDER BY rating, sentiment_label;"
```

Inspecter quelques avis :

```powershell
docker-compose exec postgres_db psql -U admin -d satisfaction_client -c "SELECT review_id, rating, sentiment_label, sentiment_score, LEFT(verbatim, 180) AS verbatim FROM fact_reviews WHERE verbatim <> '' ORDER BY review_id LIMIT 20;"
```

Réinitialiser les avis en base :

```powershell
docker-compose exec postgres_db psql -U admin -d satisfaction_client -c "TRUNCATE TABLE fact_reviews RESTART IDENTITY;"
```

## Données et Annotations

Le projet contient plusieurs fichiers de données utiles :

- `annotations_manual_labels.csv` : annotations manuelles initiales.
- `annotations_training.csv` : corpus consolidé utilisé pour l'entraînement final.
- `annotations_training.backup_before_*.csv` : sauvegardes avant enrichissement du corpus.
- `data/showroom_reviews.json` : avis historiques Showroomprivé.
- `data/external/*_reviews.json` : avis externes scrapés.
- `data/external/*_predictions.csv` : prédictions générées par le modèle.
- `data/external/*_annotated_codex.csv` : annotations ajoutées pour renforcer le corpus.
- `data/external/*_skipped_low_confidence.csv` : cas exclus de l'entraînement car trop ambigus ou peu informatifs.

Les entreprises externes déjà utilisées pour tester ou enrichir le modèle incluent notamment :

- La Bonne Allure
- Decathlon
- Intersport
- Cdiscount
- Darty

## Méthodologie Modèle

Le modèle actuel est un pipeline scikit-learn :

- `TfidfVectorizer` sur les verbatims ;
- `OneHotEncoder` sur la note client ;
- `LogisticRegression` avec `class_weight="balanced"`.

La note client est volontairement faiblement pondérée :

```text
RATING_FEATURE_WEIGHT = 0.25
```

Cette approche permet de garder la note comme signal de contexte, sans écraser le sens du texte.

Après la prédiction ML, `sentiment_analysis.py` applique des règles de sécurité métier pour éviter les incohérences les plus visibles dans le dashboard.

## Workflow Recommandé

Pour améliorer le modèle progressivement :

1. Scraper une nouvelle entreprise externe.
2. Afficher le résultat dans le dashboard.
3. Corriger directement les prédictions incohérentes dans le tableau d'avis.
4. Exporter les corrections si besoin pour audit.
5. Réentraîner le modèle avec `app/train_model.py`.
6. Retester sur une autre entreprise inconnue.

Ce cycle évite d'optimiser uniquement sur une entreprise donnée et rend le modèle plus robuste hors du dataset initial.

## Notes

- Les avertissements Docker Compose sur l'attribut `version` sont non bloquants.
- Les verbatims vides ne sont pas utilisés pour entraîner le modèle ; ils sont classés par fallback à partir de la note.
- Les fichiers CSV sont encodés en UTF-8 avec BOM lorsque c'est utile pour faciliter l'ouverture sous Excel/Windows.
- Le scraping dépend de la structure HTML de Trustpilot, donc il peut nécessiter des ajustements si le site évolue.

# Satisfaction Client

Application B2B d'analyse d'avis clients.

Le projet est parti d'un scraper Trustpilot, mais l'objectif actuel est plus large : fournir une vraie application client capable de collecter ou importer des avis, analyser la satisfaction, faire ressortir les irritants operationnels, suivre les alertes metier et ameliorer le modele avec des corrections humaines.

## Sommaire

- [Vision produit](#vision-produit)
- [Fonctionnalites principales](#fonctionnalites-principales)
- [Architecture](#architecture)
- [Structure du repo](#structure-du-repo)
- [Prerequis](#prerequis)
- [Demarrage local](#demarrage-local)
- [Authentification et espace client](#authentification-et-espace-client)
- [Sources d'avis](#sources-davis)
- [API produit](#api-produit)
- [Modele IA](#modele-ia)
- [Base de donnees et schema](#base-de-donnees-et-schema)
- [Tests et validation](#tests-et-validation)
- [Scripts historiques](#scripts-historiques)
- [Variables d'environnement](#variables-denvironnement)
- [CI GitHub Actions](#ci-github-actions)
- [Limites connues](#limites-connues)
- [Documentation agent](#documentation-agent)

## Vision produit

Satisfaction Client aide une entreprise a transformer des avis clients disperses en informations actionnables :

- prioriser les irritants clients ;
- reperer les avis critiques ;
- suivre l'evolution d'une entreprise dans le temps ;
- comparer plusieurs analyses ;
- corriger les predictions du modele ;
- relancer un entrainement controle ;
- centraliser les signaux dans un cockpit client.

La cible produit actuelle est un SaaS B2B multi-clients. Chaque organisation voit ses propres runs, avis, corrections, sources et alertes.

## Fonctionnalites principales

### Produit client

- Connexion email/mot de passe avec JWT.
- Organisations et utilisateurs.
- Roles `admin` et `member`.
- Invitations locales pour creer des utilisateurs.
- Isolation des donnees par organisation.
- Sidebar produit avec espaces Accueil, Analyses, Benchmark, Qualite IA et Administration.
- Parcours de demarrage client.
- Centre d'action client.
- Journal d'activite organisation.

### Collecte et import

- Analyse Trustpilot par URL ou nom d'entreprise.
- Import CSV avec controle avant import.
- Mapping manuel des colonnes CSV.
- Sources d'avis configurables par organisation.
- Sources actives : Trustpilot et CSV.
- Sources preparees : Google Reviews, Zendesk, Shopify, support interne.

### Analyse et restitution

- Rapport entreprise.
- KPIs : volume, note moyenne, confiance IA, reponses entreprise, score sante.
- Sentiment global.
- Repartition par note.
- Irritants detectes.
- Avis critiques.
- Incoherences note / texte.
- Tendances par rapport au run precedent.
- Benchmark multi-runs.
- Exports CSV.
- Rapport imprimable PDF cote navigateur.

### Qualite IA

- Corrections humaines des avis.
- Tableau de qualite IA.
- Export des corrections.
- Reentrainement depuis l'interface.
- Suivi de la version MLflow en production.
- Historique des entrainements.

### Alertes metier

- Alertes ouvertes par organisation.
- Regeneration des alertes d'un run.
- Acquittement et resolution par admin.
- Lecture seule pour les membres.
- Signaux principaux : part negative elevee, score sante faible, irritant dominant, absence de reponse entreprise, confiance faible, tendance negative.

## Architecture

```text
Frontend React/Vite
        |
        v
FastAPI produit
        |
        +---- PostgreSQL
        |
        +---- Redis
                |
                v
            Celery worker
                |
                +---- Scraping Trustpilot / Import CSV
                +---- Prediction scikit-learn via MLflow
                +---- Reentrainement modele

MLflow stocke les runs et la version de production du modele.
Streamlit existe encore comme dashboard historique, mais React est l'interface produit principale.
```

## Services Docker

| Service | Role |
| --- | --- |
| `frontend` | Application React/Vite. |
| `api` | API FastAPI produit. |
| `celery_worker` | Jobs asynchrones d'analyse et d'entrainement. |
| `redis` | Broker Celery et backend de resultats. |
| `postgres_db` | Base relationnelle produit et historique. |
| `mlflow` | Tracking et registry du modele. |
| `worker` | Scripts Python historiques. |
| `dashboard` | Dashboard Streamlit historique. |

## Structure du repo

```text
.
|-- app/
|   |-- api/
|   |   |-- routes/
|   |   |-- services/
|   |   |-- auth.py
|   |   |-- database.py
|   |   |-- main.py
|   |   |-- schemas.py
|   |   `-- tasks.py
|   |-- external_trustpilot.py
|   |-- sentiment_analysis.py
|   |-- train_model.py
|   `-- ...
|-- data/
|-- frontend/
|   |-- src/
|   |-- package.json
|   `-- vite.config.ts
|-- tests/
|-- docker-compose.yml
|-- Dockerfile
|-- init_db.sql
|-- requirements.txt
|-- requirements-dev.txt
|-- README.md
|-- AGENT_CONTEXT.md
|-- CURRENT_TASK.md
`-- ARCHITECTURE_DECISIONS.md
```

## Prerequis

- Docker Desktop.
- Docker Compose.
- Node.js et npm si le frontend est teste hors conteneur.
- Git.

Le projet est developpe sous Windows/PowerShell, mais les services tournent dans Docker.

## Demarrage local

Depuis la racine du repo :

```powershell
docker-compose up -d --build postgres_db mlflow redis celery_worker api frontend
```

Verifier les services :

```powershell
docker-compose ps
Invoke-RestMethod http://localhost:8000/health
```

URLs utiles :

| Service | URL |
| --- | --- |
| Frontend produit | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Healthcheck API | http://localhost:8000/health |
| MLflow | http://localhost:5000 |
| Streamlit historique | http://localhost:8501 si le service `dashboard` est lance |

Logs utiles :

```powershell
docker-compose logs -f api
docker-compose logs -f celery_worker
docker-compose logs -f frontend
```

## Authentification et espace client

L'API utilise une authentification JWT locale.

Le compte demo initial est cree au demarrage si aucun utilisateur n'existe. Les identifiants ne doivent pas etre documentes en dur dans les fichiers publics. Ils sont controles par les variables :

- `DEMO_ORG_NAME`
- `DEMO_ORG_SLUG`
- `DEMO_ADMIN_EMAIL`
- `DEMO_ADMIN_PASSWORD`
- `DEMO_ADMIN_NAME`

Le frontend stocke le JWT dans `localStorage` pour le MVP et l'envoie avec :

```text
Authorization: Bearer <token>
```

Les endpoints metier sont proteges. `/health` reste public.

Roles :

| Role | Droits principaux |
| --- | --- |
| `admin` | Lancer analyses, importer CSV, configurer sources, inviter utilisateurs, gerer alertes, corriger avis, reentrainer le modele. |
| `member` | Consulter rapports, runs, benchmark, qualite IA et administration en lecture seule selon les ecrans. |

## Sources d'avis

Sources actives :

- Trustpilot : source web publique.
- CSV : source principale pour cas B2B et exports clients.

Sources preparees, non connectees en production locale :

- Google Reviews.
- Zendesk.
- Shopify.
- Support interne.

Le CSV supporte une detection de colonnes et un mapping manuel. Les champs importants sont :

- texte de l'avis ;
- note ;
- auteur ;
- date ;
- reponse entreprise.

Les alias de colonnes sont geres dans `app/api/services/review_sources.py`.

## API produit

L'application FastAPI est definie dans `app/api/main.py`.

Principaux groupes :

- `auth` : login, session, organisation, utilisateurs, invitations.
- `review-sources` : sources d'avis par organisation.
- `analysis-runs` : analyses, imports CSV, rapports, avis, corrections, benchmark, tendances, alertes.
- `model-training` : suivi et lancement des reentrainements.

La documentation OpenAPI est disponible sur :

```text
http://localhost:8000/docs
```

## Modele IA

Le modele de sentiment est un modele scikit-learn versionne avec MLflow.

Caracteristiques :

- classification multiclasses : negatif, neutre, positif ;
- vectorisation TF-IDF ;
- note client utilisee comme signal pondere ;
- corrections humaines reintegrees avec un poids superieur ;
- version de production referencee via MLflow.

Fichiers principaux :

- `app/sentiment_analysis.py`
- `app/train_model.py`
- `app/api/services/training_service.py`
- `app/api/routes/model_training.py`

Le modele local peut modifier `app/models/sentiment_model.pkl` apres entrainement. Ne pas committer ce fichier par reflexe : verifier si la modification du modele est voulue.

## Base de donnees et schema

Le schema initial est dans :

```text
init_db.sql
```

Le schema produit est aussi maintenu de maniere idempotente au demarrage de l'API par :

```text
app/api/database.py
```

Il n'y a pas de framework de migration type Alembic pour le moment.

Tables produit principales :

- `organizations`
- `organization_review_sources`
- `users`
- `companies`
- `analysis_runs`
- `analysis_run_events`
- `reviews`
- `sentiment_predictions`
- `review_topics`
- `review_feedback`
- `business_alerts`
- `audit_events`
- `model_training_runs`

Tables historiques conservees :

- `dim_companies`
- `fact_reviews`

## Tests et validation

### Build frontend

```powershell
npm --prefix frontend run build
```

### Tests backend dans Docker

```powershell
docker-compose run --rm api sh -c "python -m pip install --disable-pip-version-check -q --timeout 120 --retries 5 -r requirements-dev.txt && python -m compileall app/api && pytest -q"
```

### Verification whitespace Git

```powershell
git diff --check
```

### Tests disponibles

- `tests/test_api_routes.py`
- `tests/test_csv_import.py`

### Non configure actuellement

- Pas de script `lint` frontend.
- Pas de tests frontend automatises.
- Pas de migrations Alembic.

## Scripts historiques

Ces scripts existent encore pour audit, demo ou operations ponctuelles :

```powershell
docker-compose run --rm worker python /app/app/main.py
docker-compose up -d dashboard
docker-compose run --rm worker python /app/app/train_model.py
docker-compose run --rm worker python /app/app/external_trustpilot.py --company https://fr.trustpilot.com/review/www.darty.com --pages-per-star 1 --sync-db --replace-db
docker-compose run --rm worker python /app/app/compare_sentiment_modes.py --source db
```

L'interface React + API FastAPI est la cible produit actuelle. Le dashboard Streamlit est historique.

## Variables d'environnement

Principales variables utilisees :

| Variable | Usage |
| --- | --- |
| `DB_HOST` | Host PostgreSQL. |
| `DB_NAME` | Base PostgreSQL. |
| `DB_USER` | Utilisateur PostgreSQL. |
| `DB_PASSWORD` | Mot de passe PostgreSQL. |
| `MLFLOW_TRACKING_URI` | URI MLflow. |
| `CELERY_BROKER_URL` | Broker Celery. |
| `CELERY_RESULT_BACKEND` | Backend resultats Celery. |
| `API_KEY` | Ancienne protection API key, gardee pour compatibilite interne. |
| `JWT_SECRET_KEY` | Secret de signature JWT. |
| `JWT_EXPIRE_MINUTES` | Duree d'expiration des tokens. |
| `INVITATION_EXPIRE_DAYS` | Duree de validite des invitations. |
| `FRONTEND_BASE_URL` | Base URL pour les liens d'invitation. |
| `DEMO_ORG_NAME` | Organisation demo initiale. |
| `DEMO_ORG_SLUG` | Slug organisation demo. |
| `DEMO_ADMIN_EMAIL` | Email admin demo. |
| `DEMO_ADMIN_PASSWORD` | Mot de passe admin demo. |
| `DEMO_ADMIN_NAME` | Nom admin demo. |
| `VITE_API_BASE_URL` | Base URL API cote frontend. |
| `FEEDBACK_SAMPLE_WEIGHT` | Poids des corrections humaines dans l'entrainement. |

Ne pas publier de vraies valeurs de secrets. Les valeurs locales de developpement doivent etre remplacees avant toute mise en production.

## CI GitHub Actions

Le workflow CI est dans :

```text
.github/workflows/ci.yml
```

Jobs actuels :

- backend tests ;
- frontend build ;
- docker build.

## Limites connues

- Le scraping Trustpilot depend de la structure HTML du site.
- Les vrais connecteurs Google/Zendesk/Shopify ne sont pas encore branches.
- Le stockage JWT en `localStorage` est acceptable pour le MVP local, pas pour un SaaS durci.
- Pas de paiement, abonnement, facturation ou gestion multi-org globale avancee.
- Pas de deploiement cloud automatise.
- Pas de monitoring technique complet.
- Pas de politique RGPD/retention formalisee.
- Les migrations sont gerees par SQL idempotent au demarrage, pas par un outil dedie.

## Documentation agent

Pour les prochains agents IA, lire dans cet ordre :

1. `AGENT_CONTEXT.md`
2. `CURRENT_TASK.md`
3. `ARCHITECTURE_DECISIONS.md`
4. `README.md`

Ces fichiers decrivent le contexte produit, les choix techniques, l'etat courant, les commandes de validation et les limites a respecter.

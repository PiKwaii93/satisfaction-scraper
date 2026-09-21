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
|-- migrations/
|-- alembic.ini
|-- docker-compose.yml
|-- Dockerfile
|-- init_db.sql
|-- requirements.txt
|-- requirements-dev.txt
|-- README.md
|-- AGENT_CONTEXT.md
|-- PRODUCT_ROADMAP.md
|-- ARCHITECTURE_DECISIONS.md
`-- CURRENT_TASK.md
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
docker-compose up -d --build postgres_db mlflow redis model_bootstrap api celery_worker frontend
```

Verifier les services :

```powershell
docker-compose ps
Invoke-RestMethod http://localhost:8000/health
```

Pour un premier demarrage, copier `.env.example` vers `.env` et adapter les
identifiants, secrets et ports exposes si necessaire. Compose lit directement
ces variables. `DB_HOST=postgres_db` et `MLFLOW_TRACKING_URI=http://mlflow:5000`
designent les services internes ; les ports `*_HOST_PORT` ne changent que les
acces depuis la machine hote. `DATABASE_URL` n'est pas utilise par l'API : elle
assemble sa connexion depuis `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` et
`DB_PASSWORD`.

Le demarrage attend PostgreSQL, Redis et MLflow, puis le job `model_bootstrap`.
L'API applique les migrations jusqu'au head Alembic et initialise les comptes
de demonstration. Le bootstrap enregistre le pickle versionne dans MLflow
seulement si l'alias `sentiment_model@production` est absent. Il verifie d'abord
l'empreinte dans `app/models/sentiment_model.sha256`, puis charge le modele par
son URI MLflow. Si l'alias existe deja, il verifie son chargement et ne cree
aucune version. Il n'entraine jamais le modele. `/health` teste la connexion
PostgreSQL par `SELECT 1` ; Redis et MLflow sont controles par leurs sondes
Compose au demarrage.

Pour demontrer un cold start sans utiliser les volumes locaux habituels, choisir
un nom de projet distinct et des ports hote libres :

```powershell
$env:POSTGRES_HOST_PORT="15432"
$env:MLFLOW_HOST_PORT="15000"
$env:REDIS_HOST_PORT="16379"
$env:API_HOST_PORT="18000"
$env:FRONTEND_HOST_PORT="15173"
$env:VITE_API_BASE_URL="http://localhost:18000"
$env:FRONTEND_BASE_URL="http://localhost:15173"
docker-compose -p satisfaction_coldstart up -d --build postgres_db mlflow redis model_bootstrap api celery_worker frontend
docker-compose -p satisfaction_coldstart ps
docker-compose -p satisfaction_coldstart run --rm --no-deps api alembic current
Invoke-RestMethod http://localhost:18000/health

# Reprise sur les memes volumes : le bootstrap ne cree pas de nouvelle version.
docker-compose -p satisfaction_coldstart stop
docker-compose -p satisfaction_coldstart up -d postgres_db mlflow redis model_bootstrap api celery_worker frontend

# Seulement pour ce projet temporaire, apres verification du nom de projet.
docker-compose -p satisfaction_coldstart down -v
```

Le frontend Vite lit `VITE_API_BASE_URL` lors du lancement. Adapter aussi
`FRONTEND_BASE_URL` pour les liens d'invitation et l'origine du frontend si
necessaire. Un test CSV doit utiliser l'API et le worker du meme projet : leurs
fichiers d'import sont partages dans le volume `api_data`.

### Validation reproductible

Une seule commande construit et demarre un projet Compose isole, execute les
tests backend (dont les migrations sur des bases temporaires), les tests et le
build frontend, puis rejoue le parcours HTTP CSV jusqu'au run `completed` et a
sa synthese. Le script fixe des ports de test distincts, affiche `PASS` ou
l'etape en echec et supprime uniquement son projet Compose temporaire :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-repro.ps1
```

La CI lance automatiquement `python -m pytest -q tests`, les tests frontend et
le build. Le job `e2e-smoke` de la CI se lance manuellement et execute la
meme commande isolee, car le build des images et MLflow allongent ce controle.
Pour les tests backend hors Docker, disposer d'un PostgreSQL de test distinct,
installer `requirements-dev.txt`, definir `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME` et `DEMO_ADMIN_PASSWORD`, puis lancer
`python -m pytest -q tests`. Les tests de migration creent, utilisent et
suppriment leurs propres bases sur ce serveur de test.

### Deploiement sur une VM de test existante

Le workflow manuel `Deploy test VM` prend le SHA exact de `main` et refuse de
deployer si le run CI automatique de ce SHA n'a pas reussi. Il prepare une VM
Linux existante avec `deploy/prepare-test-vm.yml`, transfere une archive Git
dans `~/satisfaction-test/releases/<SHA>`, puis lance Compose avec le nom de
projet stable `satisfaction-test`. Les volumes PostgreSQL, MLflow et imports
restent ainsi en place entre les revisions. Le fichier de configuration est
stocke hors Git dans `~/satisfaction-test/shared/test.env` (mode 600).

Prerequis : VM Ubuntu 24.04 (4 vCPU, 8 Go de RAM, 50 Go de disque recommandes),
Docker Engine et le plugin `docker compose` installes, utilisateur SSH autorise
a utiliser Docker sans `sudo`, `tar` et `curl`. Le playbook verifie Docker et
Compose puis cree les repertoires de maniere idempotente ; il ne cree pas de VM
et n'installe pas Docker. Le seul port entrant necessaire est SSH (22). Compose
lie PostgreSQL 5432, Redis 6379, MLflow 5000, API 8000 et frontend 5173 a
`127.0.0.1` sur la VM. Pour consulter l'application, ouvrir un tunnel :

```bash
ssh -L 5173:127.0.0.1:5173 -L 8000:127.0.0.1:8000 utilisateur@hote
```

Configurer l'environnement GitHub `test` avec les secrets `TEST_HOST`,
`TEST_USER`, `TEST_SSH_KEY`, `TEST_SSH_KNOWN_HOSTS` (cle hote SSH verifiee) et
`TEST_ENV_FILE` (contenu du fichier Compose, jamais versionne). Ce dernier
doit au minimum definir `DB_USER`, `DB_NAME`, `DB_PASSWORD`, `JWT_SECRET_KEY`,
`DEMO_ADMIN_PASSWORD`, `PLATFORM_ADMIN_PASSWORD` et `API_KEY`. Utiliser des
valeurs de test propres a la VM, differentes des valeurs de demonstration.
Ne pas y mettre de variable `*_HOST_PORT` pour ouvrir les services : le script
de deploiement impose l'interface loopback. Le frontend et les liens utilisent
`localhost` via le tunnel SSH.

Premier deploiement : versionner et pousser les fichiers de ce chantier sur
`main`, preparer la VM et ses acces SSH/Docker, creer les secrets ci-dessus,
verifier que la CI automatique de ce nouveau SHA a reussi, puis lancer
manuellement `Deploy test VM` sur la branche `main` dans GitHub Actions. Le
resume du job donne le SHA, l'heure UTC, l'environnement et le resultat des
healthchecks. Sur la VM, `~/satisfaction-test/current.sha` indique le SHA
valide et `previous.sha` le precedent. Le script construit les images avant
de mettre a jour les conteneurs, attend les sondes Compose et teste `/health`
ainsi que la page frontend. Il n'enregistre le nouveau SHA qu'apres succes.
En cas d'echec, il tente de reactiver l'ancienne revision et laisse le job en
echec ; aucune reussite n'est annoncee sans healthcheck. Au tout premier
deploiement, aucun SHA precedent n'existe encore pour un rollback automatique.

```bash
gh workflow run deploy-test.yml --ref main
```

Rollback manuel vers le SHA precedent, depuis la VM :

```bash
cd ~/satisfaction-test
current=$(cat current.sha)
bash "releases/$current/deploy/test-deploy.sh" rollback
```

Le rollback reconstruit les images de l'ancienne revision, relance les services
applicatifs et verifie les healthchecks sans supprimer les volumes ni restaurer
la base. Aucun downgrade Alembic n'est effectue. **Limite :** l'API applique
les migrations au demarrage ; si une nouvelle migration rend l'ancien code
incompatible avec le schema, le rollback applicatif peut echouer. Une telle
migration exige une procedure de donnees separee avant deploiement. Cette
strategie a un seul ensemble de conteneurs : une breve interruption reste
possible pendant leur remplacement. Ne pas changer `DB_PASSWORD` d'une base
existante via un simple redeploiement : le volume PostgreSQL conserve son mot
de passe initial.

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
- `PLATFORM_ADMIN_EMAIL`
- `PLATFORM_ADMIN_PASSWORD`
- `PLATFORM_ADMIN_NAME`

Le frontend stocke le JWT dans `localStorage` pour le MVP et l'envoie avec :

```text
Authorization: Bearer <token>
```

Les endpoints metier sont proteges. `/health` reste public.

Roles :

| Role | Droits principaux |
| --- | --- |
| `platform_admin` | Acceder au backoffice plateforme, suivre les organisations clientes, changer les plans et traiter les demandes d'upgrade. |
| `admin` | Lancer analyses, importer CSV, configurer sources, inviter utilisateurs, gerer alertes, corriger avis, reentrainer le modele. |
| `member` | Consulter rapports, runs, benchmark, qualite IA et administration en lecture seule selon les ecrans. |

### Plans et limites d'usage

Chaque organisation possede un plan produit. Les plans controlent les volumes
mensuels, le nombre de membres et l'acces a certaines fonctionnalites avancees.

Plans disponibles :

| Plan | Usage cible | Limites principales |
| --- | --- | --- |
| `free` | Essai local ou petite demo. | 3 analyses/mois, 300 avis/mois, 100 avis par CSV, 1 membre, pas de benchmark ni reentrainement. |
| `pro` | Petite equipe metier. | 50 analyses/mois, 10 000 avis/mois, 2 000 avis par CSV, 5 membres, benchmark active, reentrainement reserve. |
| `business` | Espace client complet. | Analyses sans limite mensuelle stricte, 100 000 avis/mois, 10 000 avis par CSV, 25 membres, benchmark et reentrainement actifs. |

L'API refuse les operations qui depassent le plan de l'organisation courante
avec une erreur `403`. Le frontend affiche l'usage de l'espace client dans
l'administration.

## Sources d'avis

Sources actives :

- Trustpilot : source web publique.
- CSV : source principale pour cas B2B et exports clients.

Sources preparees, non connectees en production locale :

- Google Reviews.
- Zendesk.
- Shopify.
- Support interne.

Le CSV supporte une detection de colonnes, un mapping manuel et un profil de mapping sauvegarde par organisation pour reutiliser les colonnes habituelles sur les imports suivants. Les champs importants sont :

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

Le schema produit est versionne avec Alembic. Les revisions sont dans :

```text
migrations/versions/
```

Au demarrage, l'API et les workers appellent :

```text
app/api/database.py
```

Ce module applique automatiquement les migrations jusqu'a `head`. Pour une base
locale existante sans table `alembic_version`, il valide d'abord les tables,
colonnes et index attendus, puis pose la baseline sans recreer les tables ni
modifier les donnees. Un schema partiel ou incompatible bloque le demarrage avec
une erreur explicite.

`init_db.sql` ne contient plus que les tables historiques utilisees par les
anciens scripts :

- `dim_companies`
- `fact_reviews`

Commandes de migration :

```powershell
# Appliquer les migrations ou baseliner une base existante valide
docker-compose run --rm api python -m app.api.schema_migrations upgrade

# Afficher la revision courante et la revision cible
docker-compose run --rm api python -m app.api.schema_migrations current

# Revenir d'une revision, uniquement avec confirmation explicite
docker-compose run --rm api python -m app.api.schema_migrations downgrade --revision -1 --yes
```

Un downgrade peut supprimer des tables et des donnees produit. Il doit etre
precede d'une sauvegarde PostgreSQL et ne doit pas etre lance machinalement.

### Sauvegarde, restauration et diagnostic

Les donnees produit sont maintenant importantes : organisations, utilisateurs,
runs, avis, corrections humaines et entrainements. Avant une migration risquee
ou une manipulation de schema, creer un dump PostgreSQL local.

Les dumps sont generes dans `backups/` et ignores par Git.

```powershell
# Creer un backup horodate de la base satisfaction_client
powershell -ExecutionPolicy Bypass -File .\scripts\ops\backup-db.ps1

# Verifier rapidement l'etat de la base
powershell -ExecutionPolicy Bypass -File .\scripts\ops\db-diagnostics.ps1

# Restaurer un backup, avec confirmation interactive
powershell -ExecutionPolicy Bypass -File .\scripts\ops\restore-db.ps1 -BackupFile .\backups\satisfaction_client-YYYYMMDD-HHMMSS.dump

# Restaurer sans confirmation interactive
powershell -ExecutionPolicy Bypass -File .\scripts\ops\restore-db.ps1 -BackupFile .\backups\satisfaction_client-YYYYMMDD-HHMMSS.dump -Yes
```

Le diagnostic affiche :

- la revision Alembic courante ;
- les volumes des tables produit principales ;
- les derniers runs d'analyse.

La restauration remplace les objets existants de la base cible. Elle est faite
pour un environnement local ou de demonstration, pas pour une production sans
procedure de sauvegarde externe.

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

## Tests et validation

### Build frontend

```powershell
npm --prefix frontend run build
```

### Tests frontend

```powershell
npm --prefix frontend test
```

La fondation frontend utilise Vitest, React Testing Library et MSW. Les tests
couvrent actuellement la connexion, la restauration de session, les permissions
`admin` / `member`, l'expiration `401` et le lancement d'une analyse Trustpilot.

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
- `tests/test_database_migrations.py`
- `frontend/src/App.test.tsx`
- `frontend/src/api.test.ts`

### Non configure actuellement

- Pas de script `lint` frontend.

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

Un exemple local est fourni dans `.env.example`. Il sert de reference pour les
secrets et URLs attendus, sans contenir de valeur de production.

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
| `PLATFORM_ADMIN_EMAIL` | Email admin plateforme pour le backoffice interne. |
| `PLATFORM_ADMIN_PASSWORD` | Mot de passe admin plateforme. |
| `PLATFORM_ADMIN_NAME` | Nom admin plateforme. |
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
- frontend tests et build ;
- docker build.

## Limites connues

- Le scraping Trustpilot depend de la structure HTML du site.
- Les vrais connecteurs Google/Zendesk/Shopify ne sont pas encore branches.
- Le stockage JWT en `localStorage` est acceptable pour le MVP local, pas pour un SaaS durci.
- Pas de paiement, abonnement, facturation ou gestion multi-org globale avancee.
- Pas de deploiement cloud automatise.
- Pas de monitoring technique complet.
- Pas de politique RGPD/retention formalisee.

## Documentation agent

Pour les prochains agents IA, lire dans cet ordre :

1. `README.md`
2. `AGENT_CONTEXT.md`
3. `PRODUCT_ROADMAP.md`
4. `ARCHITECTURE_DECISIONS.md`
5. `CURRENT_TASK.md`

Ces fichiers decrivent respectivement :

- le produit, son architecture et son fonctionnement ;
- les regles stables de travail pour les agents ;
- la trajectoire produit et les priorites ;
- les decisions structurantes ;
- la tache operationnelle en cours.

Le code, Git et les tests restent les sources de verite.

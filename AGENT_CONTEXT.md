# Agent Context - Satisfaction Client

Ce fichier sert de passation pour tout agent IA travaillant sur ce repo.

## Regle principale

Le code existant est la source de verite. Si une conversation ancienne contredit le code, privilegier le code et documenter l'ecart.

Avant toute modification :

1. Lire `README.md`.
2. Lire `CURRENT_TASK.md`.
3. Lire `ARCHITECTURE_DECISIONS.md`.
4. Verifier l'etat Git.
5. Inspecter le code concerne.

Ne pas lancer de refonte massive sans demande explicite.

## Etat produit

Le projet est devenu une application produit B2B multi-clients, pas seulement un scraper.

Nom produit : Satisfaction Client.

Objectif : aider une entreprise a analyser ses avis clients, comprendre ses irritants, suivre les alertes et ameliorer progressivement le modele de sentiment.

Le repo contient encore des elements historiques du projet initial :

- scripts de scraping ;
- dashboard Streamlit ;
- tables `dim_companies` et `fact_reviews` ;
- exports JSON/CSV ;
- scripts d'entrainement.

Ces elements ne doivent pas etre supprimes sans decision explicite. Ils peuvent servir pour audit, demonstration ou compatibilite.

## Etat Git confirme avant cette documentation

Historique recent confirme par `git log --oneline --decorate -20` :

```text
6d658f7 (HEAD -> codex/platform-organizations, origin/main, origin/HEAD, main) Merge pull request #35 from PiKwaii93/codex/actionable-home
1230fa9 (origin/codex/actionable-home) feat: consolidate home action cockpit
e252edc Merge pull request #34 from PiKwaii93/codex/product-navigation
c064bf1 (origin/codex/product-navigation) feat: add product workspace navigation
62ab87a Merge pull request #33 from PiKwaii93/codex/client-onboarding
a245278 (origin/codex/client-onboarding) feat: add client onboarding checklist
f0ca815 Merge pull request #32 from PiKwaii93/codex/org-review-sources
fc89a58 (origin/codex/org-review-sources) feat: add organization review source settings
11ce373 Merge pull request #31 from PiKwaii93/codex/action-center
490dc41 (origin/codex/action-center) feat: add client action center
8507088 Merge pull request #30 from PiKwaii93/codex/business-alerts
31d240d (origin/codex/business-alerts, codex/business-alerts) feat: add business alerts
0524313 Merge pull request #29 from PiKwaii93/codex/org-settings-audit
a507ace (origin/codex/org-settings-audit) feat: add organization settings and audit log
5d2104a Merge pull request #28 from PiKwaii93/codex/role-permissions
431c5dd (origin/codex/role-permissions) feat: add role-based permissions
b466ab8 Merge pull request #27 from PiKwaii93/codex/user-roles-invitations
87d496d (origin/codex/user-roles-invitations, codex/user-roles-invitations) feat: add organization invitations
8c23565 Merge pull request #26 from PiKwaii93/codex/run-trends
b50d90d (origin/codex/run-trends, codex/run-trends) feat: add run trend comparison
```

Avant la creation de cette documentation, `git diff --stat` et `git diff --name-status` etaient vides.

## Architecture reelle

### Frontend

- Dossier : `frontend/`
- Stack : React, Vite, TypeScript, lucide-react.
- Entree principale : `frontend/src/App.tsx`.
- API client : `frontend/src/api.ts`.
- Types : `frontend/src/types.ts`.
- Styles : `frontend/src/styles.css`.

Le frontend est encore monolithique dans `App.tsx`. Eviter d'ajouter une complexite excessive sans refactor planifie.

### Backend produit

- Dossier : `app/api/`
- Framework : FastAPI.
- Entree principale : `app/api/main.py`.
- Auth : `app/api/auth.py`.
- Schema DB : `app/api/database.py`.
- Schemas Pydantic : `app/api/schemas.py`.
- Celery : `app/api/celery_app.py`, `app/api/tasks.py`.
- Routes :
  - `app/api/routes/auth.py`
  - `app/api/routes/review_sources.py`
  - `app/api/routes/analysis_runs.py`
  - `app/api/routes/model_training.py`

### Services backend importants

- `app/api/services/analysis_service.py` : creation, execution, consultation des runs.
- `app/api/services/insights.py` : syntheses metier.
- `app/api/services/review_sources.py` : sources d'avis et CSV.
- `app/api/services/alert_service.py` : alertes metier.
- `app/api/services/action_center_service.py` : centre d'action client.
- `app/api/services/organization_service.py` : audit organisation.
- `app/api/services/training_service.py` : reentrainement modele.
- `app/api/services/job_queue.py` : etat Celery.

### IA et data

- `app/sentiment_analysis.py` : chargement et prediction du modele.
- `app/train_model.py` : entrainement, MLflow, feedback.
- `app/external_trustpilot.py` : scraping externe Trustpilot.
- `app/compare_sentiment_modes.py` : audit de modes sentiment.

### Base de donnees

- Initialisation SQL : `init_db.sql`.
- Evolution idempotente : `app/api/database.py`.
- Pas de migration Alembic.

### Runtime Docker

- `docker-compose.yml`.
- `Dockerfile`.
- `frontend/Dockerfile`.

## Authentification et droits

L'API produit utilise JWT.

Endpoints publics :

- `GET /health`
- `POST /auth/login`
- `POST /auth/invitations/accept`

Endpoints metier :

- proteges par `Authorization: Bearer <token>` ;
- filtres par `organization_id` ;
- certains endpoints demandent le role `admin`.

Ne pas revenir a une API key frontend. Le helper API key dans `app/api/security.py` est un vestige ou compatibilite interne, pas le chemin produit principal.

## Isolation multi-tenant

Chaque utilisateur est rattache a une organisation.

Les requetes doivent filtrer par `current_user.organization_id` pour :

- entreprises ;
- runs ;
- avis ;
- corrections ;
- alertes ;
- sources ;
- benchmark ;
- entrainement ou origine de l'entrainement si applicable.

Verifier ce point a chaque ajout d'endpoint.

## Sources d'avis

Sources actives :

- Trustpilot.
- CSV.

Sources preparees :

- Google Reviews.
- Zendesk.
- Shopify.
- Support interne.

Ne pas annoncer un connecteur comme fonctionnel si le code ne l'execute pas vraiment. Les connecteurs non branches doivent rester documentes comme "planned" ou "prepare".

## Modele IA

Le modele en production vient de MLflow :

```text
models:/sentiment_model@production
```

`app/models/sentiment_model.pkl` peut etre modifie par des entrainements locaux. Ne pas le committer sauf si la demande vise explicitement une nouvelle version de modele versionnee dans Git.

Les corrections humaines servent au reentrainement avec un poids superieur. Le poids est configurable.

## Decisions deja prises

- React/Vite/TypeScript est l'interface produit principale.
- Streamlit est historique.
- FastAPI est le backend produit.
- Celery + Redis gerent les jobs longs.
- PostgreSQL est la base produit.
- MLflow gere le versioning modele.
- JWT local est l'auth MVP.
- Trustpilot + CSV sont les sources actives.
- Les autres sources sont preparees mais non branchees.
- Le produit vise un SaaS B2B multi-clients.

## Commandes de validation

Depuis la racine :

```powershell
npm --prefix frontend run build
```

```powershell
docker-compose run --rm api sh -c "python -m pip install --disable-pip-version-check -q --timeout 120 --retries 5 -r requirements-dev.txt && python -m compileall app/api && pytest -q"
```

```powershell
git diff --check
```

Pour lancer l'app :

```powershell
docker-compose up -d --build postgres_db mlflow redis celery_worker api frontend
```

## Tests existants

- `tests/test_api_routes.py`
- `tests/test_csv_import.py`

Les tests backend couvrent deja plusieurs aspects critiques :

- login ;
- invitations ;
- users ;
- settings ;
- sources ;
- permissions admin/member ;
- analyses ;
- import CSV ;
- feedback ;
- alertes ;
- tendances.

Il n'y a pas de tests frontend automatises ni de lint configure.

## Sensible data

Ne jamais copier de valeurs de secrets dans les docs ou les reponses finales.

Le repo contient des noms de variables de secrets et des valeurs locales de developpement dans Docker Compose ou le code de seed. Les documenter par nom de variable seulement.

Variables sensibles ou a traiter comme sensibles :

- `DB_PASSWORD`
- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `DEMO_ADMIN_PASSWORD`
- `API_KEY`
- tokens d'invitation ;
- tout secret de connecteur futur.

## Style de travail attendu

- Lire avant d'editer.
- Garder les modifications scopees.
- Ne pas melanger feature, refactor et docs dans le meme commit sauf demande.
- Ne pas casser les scripts historiques.
- Ne pas supprimer les donnees d'exemple sans raison.
- Toujours verifier `git status` avant de finir.
- Ne pas commit/push sans accord utilisateur.

## Risques frequents

- Oublier le filtre `organization_id`.
- Casser les tests de permissions admin/member.
- Confondre sources preparees et sources actives.
- Committer `app/models/sentiment_model.pkl` par accident apres entrainement local.
- Ajouter une route sans schema Pydantic.
- Documenter une commande non testee comme si elle etait verifiee.
- Exposer des valeurs de secrets dans README ou logs.

# Rapport technique - Satisfaction Client

## 1. Objectif du projet

Le projet Satisfaction Client transforme des avis clients non structures en indicateurs exploitables pour une entreprise. Il permet de collecter ou importer des avis, de les analyser avec un modele de sentiment proprietaire, de restituer les resultats dans une application web et d'alimenter une boucle d'amelioration continue via des corrections humaines.

La solution repond a une problematique de satisfaction client en aval de la supply chain : comprendre rapidement les irritants lies a la livraison, au service client, au prix, au remboursement, a la qualite produit ou a la conformite des commandes.

## 2. Architecture generale

Le projet est orchestre avec Docker Compose et se compose de plusieurs services complementaires.

| Service | Technologie | Role |
| --- | --- | --- |
| `frontend` | React, Vite, TypeScript | Interface produit pour lancer, comparer et corriger les analyses. |
| `api` | FastAPI | API produit, endpoints metier proteges par JWT et roles. |
| `celery_worker` | Celery | Execution asynchrone des analyses et des reentrainements. |
| `redis` | Redis | Broker et backend de resultats Celery. |
| `postgres_db` | PostgreSQL | Stockage des entreprises, runs, avis, predictions et corrections. |
| `mlflow` | MLflow | Suivi des experimentations et registre de modele. |
| `worker` | Python | Scripts historiques de scraping, ETL et entrainement. |
| `dashboard` | Streamlit | Ancienne interface d'exploration, conservee comme support historique. |

Flux principal :

```text
Utilisateur
  -> React
  -> FastAPI
  -> PostgreSQL
  -> Celery / Redis
  -> Scraping Trustpilot ou import CSV
  -> Prediction sentiment via modele MLflow
  -> PostgreSQL
  -> Rapport React, export CSV/PDF, corrections humaines
```

## 3. Sources de donnees

Deux modes d'acquisition sont disponibles.

### 3.1 Trustpilot

L'utilisateur saisit une entreprise ou une URL Trustpilot. L'API cree un run d'analyse et Celery execute le scraping avec Playwright. Le scraping peut cibler plusieurs pages par note, ce qui permet d'equilibrer les avis entre 1 et 5 etoiles.

Donnees collectees :

- auteur ;
- note ;
- date brute ;
- verbatim ;
- indicateur de reponse entreprise ;
- entreprise associee.

Une collecte privee distincte du pipeline produit a ensuite parcouru les 16 vues linguistiques accessibles de `www.vapoter.fr` sur Trustpilot jusqu'a leur fin naturelle. Elle a sauvegarde 476 pages et, apres reconciliation hors ligne, 11 281 identifiants uniques (9 261 avis principaux et 2 020 empiles), dont 9 473 avec reponse d'entreprise. La [preuve assainie](docs/TRUSTPILOT_VAPOTER_EVIDENCE.md) publie les agregats et empreintes sans texte d'avis. Le corpus n'a pas ete importe en base ni utilise pour l'entrainement ML.

Le controle hors ligne des notes donne 289 avis a 1 etoile, 115 a 2, 239 a 3, 1 030 a 4 et 9 608 a 5. La definition operationnelle retenue pour les avis negatifs est **1 ou 2 etoiles** : 404 avis, dont 360 avec reponse d'entreprise et 44 sans reponse, soit 89,11 % de reponses visibles. Ce resultat de collecte privee n'est pas un KPI produit calcule par le dashboard.

Une observation ponctuelle du [profil Trustpilot Vapoter](https://fr.trustpilot.com/review/www.vapoter.fr), le 30 septembre 2026 a 16:27 (Europe/Paris), a releve le nom commercial Vapoter, la categorie « Magasin de cigarettes electroniques », un TrustScore de **4,8 / 5** et **11 281 avis affiches**. La repartition affichee etait : 1 etoile 3 % (289 avis), 2 etoiles 1 % (115), 3 etoiles 2 % (239), 4 etoiles 9 % (1 030), 5 etoiles 85 % (9 608) ; les comptes proviennent des infobulles. Cette concordance chiffree avec le corpus ne prouve pas un instantane identique d'identifiants. Le nom juridique complet reste non demontre.

### 3.2 CSV utilisateur

L'utilisateur peut importer un fichier CSV d'avis. Ce mode permet d'analyser des exports clients ou des avis provenant d'autres plateformes sans dependre de Trustpilot.

Le controle avant import verifie :

- le nombre total d'avis ;
- le nombre de lignes exploitables ;
- le nombre de lignes ignorees ;
- les colonnes detectees ;
- un apercu des premiers verbatims.

Les colonnes minimales attendues sont :

- texte de l'avis ;
- note, si disponible.

Les colonnes optionnelles sont :

- auteur ;
- date ;
- reponse entreprise.

## 4. Modele de donnees

L'application produit utilise un schema PostgreSQL dedie de **16 tables**,
versionne par huit migrations Alembic jusqu'a `20260921_0008`. Le tableau
ci-dessous ne presente que les tables centrales de l'analyse ; le
[catalogue complet, ses cardinalites, contraintes et diagrammes](docs/SCHEMA_DONNEES_ETL.md)
est egalement livre en [PDF](deliverables/07_Schema_Donnees_ETL.pdf).

| Table | Role |
| --- | --- |
| `companies` | Entreprises analysees et source associee. |
| `analysis_runs` | Historique des analyses, statut, duree, source et fichiers produits. |
| `analysis_run_events` | Journal d'execution lisible par l'utilisateur. |
| `reviews` | Avis individuels rattaches a un run. |
| `sentiment_predictions` | Prediction de sentiment et score du modele. |
| `review_topics` | Irritants detectes sur chaque avis. |
| `review_feedback` | Corrections humaines pour ameliorer le modele. |
| `model_training_runs` | Historique des reentrainements lances depuis l'interface. |

Ce modele separe les donnees brutes, les predictions, les corrections et les metadonnees d'execution. Il permet de conserver un historique auditable, de comparer plusieurs entreprises et de reutiliser les corrections pour le reentrainement.

Le schema produit est versionne avec Alembic. Une base existante non versionnee
est validee puis rattachee a la baseline sans recreation des tables. Les tables
historiques `dim_companies` et `fact_reviews` restent definies par
`init_db.sql` pour les anciens scripts. Elles ne sont pas les tables du produit.
Le `ON CONFLICT` de l'ancien `app/etl.py` vise une unicite absente du SQL
historique ; ce flux ne doit pas etre presente comme le chemin produit valide.

## 5. Pipeline d'analyse

1. L'utilisateur cree une analyse depuis le frontend.
2. FastAPI valide la demande et cree un `analysis_run`.
3. Si une analyse identique est deja active, l'API renvoie un conflit pour eviter les doublons.
4. Le run est envoye dans Celery.
5. Le worker collecte les avis ou relit le CSV importe.
6. Les avis sont nettoyes et normalises.
7. Le modele de sentiment charge depuis MLflow predit un label et un score.
8. Des irritants metier sont detectes par analyse lexicale.
9. Les resultats sont stockes dans PostgreSQL.
10. Le frontend affiche le rapport, les avis, les exports et le journal d'execution.

Le [diagramme ETL detaille](docs/SCHEMA_DONNEES_ETL.md) distingue la collecte
Trustpilot, l'import CSV, la normalisation, les tables produit PostgreSQL,
l'inference MLflow et la restitution API/frontend. Le lot historique de
1 200 avis a une provenance d'acquisition incomplete ; l'ancienne tentative
Showroomprive HTTP 403 n'a extrait aucun avis. Ces deux JSON ne sont pas la
preuve finale. La collecte privee Vapoter a parcouru les 16 vues accessibles
jusqu'a leur fin naturelle : 476 pages, 11 281 IDs uniques et 0 collision
inter-corpus apres reconciliation. Les compteurs UI ont evolue durant la
collecte ; ce resultat n'est pas un instantane parfaitement simultane.

Les statuts principaux d'un run sont :

- `pending` ;
- `running` ;
- `completed` ;
- `failed` ;
- `empty`.

## 6. Modele de sentiment

Le modele est un classifieur supervise scikit-learn entraine sur des avis annotes.

Caracteristiques :

- vectorisation TF-IDF des verbatims ;
- prise en compte reduite de la note client ;
- classification en trois classes : `Negatif`, `Neutre`, `Positif` ;
- evaluation par accuracy, precision, recall et F1-score ;
- serialisation locale ;
- publication dans MLflow avec alias de production.

La note client est volontairement ponderee afin que le texte garde une influence centrale. Ce choix repond au besoin metier : detecter les cas ou la note et le verbatim racontent des choses differentes.

## 7. Boucle d'amelioration humaine

L'application permet de corriger manuellement le sentiment d'un avis. Les corrections sont stockees dans `review_feedback`, exportables en CSV et integrees au prochain reentrainement.

Le reentrainement :

- combine le corpus historique annote et les corrections humaines ;
- pondere davantage les corrections recentes ;
- cree un snapshot auditable du dataset d'entrainement ;
- evalue le modele sur un split stratifie ;
- peut enregistrer une nouvelle version candidate dans MLflow ;
- ne met a jour l'alias de production et ne resynchronise les predictions qu'apres promotion explicite.

Cette boucle transforme l'application en outil d'amelioration continue plutot qu'en simple dashboard statique.

## 8. API FastAPI

L'API expose les principaux endpoints suivants.

| Endpoint | Role |
| --- | --- |
| `GET /health` | Verification de disponibilite. |
| `POST /analysis-runs` | Creation d'une analyse Trustpilot. |
| `POST /analysis-runs/preview-csv` | Controle avant import CSV. |
| `POST /analysis-runs/import-csv` | Import et analyse d'un CSV. |
| `GET /analysis-runs` | Historique des analyses. |
| `GET /analysis-runs/{run_id}` | Detail d'un run. |
| `POST /analysis-runs/{run_id}/execute` | Relance d'un run. |
| `GET /analysis-runs/{run_id}/events` | Journal d'execution. |
| `GET /analysis-runs/{run_id}/summary` | Rapport synthetique. |
| `GET /analysis-runs/{run_id}/reviews` | Avis pagines et filtrables. |
| `POST /analysis-runs/{run_id}/reviews/{review_id}/feedback` | Correction humaine. |
| `GET /analysis-runs/feedback/quality` | Synthese qualite IA. |
| `GET /analysis-runs/compare` | Benchmark multi-entreprises. |
| `GET /model-training/overview` | Etat du modele de production. |
| `POST /model-training/runs` | Lancement d'un reentrainement. |

Les endpoints metier sont proteges par des jetons JWT et des roles, avec isolation par organisation. L'endpoint `/health` reste public afin de faciliter les sondes de disponibilite.

## 9. Interface React

Le frontend React/Vite/TypeScript est l'interface principale du produit. Il permet :

- de lancer une analyse Trustpilot ;
- d'importer un CSV avec controle avant import ;
- de suivre l'historique des runs ;
- de consulter le journal d'execution ;
- de visualiser les KPIs d'un rapport entreprise ;
- de comparer plusieurs runs dans un benchmark ;
- de corriger les labels d'avis ;
- de piloter la qualite IA ;
- de declencher un reentrainement ;
- d'exporter les avis, les corrections et les rapports.

L'interface vise un usage par des profils metier : responsable service client, responsable supply chain, analyste data ou direction.

## 10. Restitution metier

Un rapport entreprise contient :

- volume d'avis analyses ;
- note moyenne ;
- confiance IA moyenne ;
- repartition des sentiments ;
- repartition par note ;
- irritants principaux ;
- avis critiques ;
- incoherences note / texte ;
- score sante ;
- priorites recommandees ;
- points de vigilance.

Le benchmark multi-entreprises permet de comparer deux a quatre runs et de detecter :

- l'entreprise la plus a risque ;
- les irritants communs ;
- les irritants propres ;
- les differences de repartition negative ;
- les signaux metier prioritaires.

## 11. Dockerisation et reproductibilite

Le projet se lance avec Docker Compose. Les services applicatifs, la base de donnees, Redis, MLflow et le frontend sont definis dans `docker-compose.yml`.

Commandes principales :

```powershell
docker-compose up -d --build api celery_worker frontend
docker-compose up -d postgres_db mlflow redis
docker-compose logs -f api
docker-compose logs -f celery_worker
```

Cette organisation rend le projet reproductible sur une autre machine equipee de Docker.

## 12. CI/CD et qualite

La CI GitHub Actions execute les tests backend, les tests et le build frontend,
puis construit l'image Docker. Un job `e2e-smoke` manuel valide un demarrage
Compose isole et un import CSV de 15 avis. Le workflow de deploiement manuel
vise une VM de test existante et verifie API et frontend. Les runs exacts et
leurs limites sont dans [les preuves DevOps](docs/DEVOPS_EVIDENCE.md).

Les validations disponibles incluent :

- build du frontend ;
- compilation Python de l'API ;
- verification `git diff --check` ;
- migrations Alembic sur bases PostgreSQL temporaires ;
- test de l'endpoint `/health` ;
- execution d'analyses Trustpilot ;
- import CSV ;
- correction humaine ;
- reentrainement ;
- export CSV et PDF.

Le script KPI extrait les temps de deploiement des runs GitHub Actions. La
supervision de test archive un JSON et un Step Summary. Le cron final de
Monitor est `17 * * * *` ; le workflow diagnostic heartbeat a ete retire.
Le [heartbeat planifie 35765192366](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35765192366)
a reussi et l'[evenement Monitor planifie 35764642522](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35764642522)
a ete cree, mais son job a ete `skipped` par `TEST_MONITOR_SCHEDULE_ENABLED=false`.
La [sonde manuelle reelle 35726582579](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35726582579)
a reussi ; aucune sonde VM planifiee active n'est prouvee. Le restart conditionnel
unique de l'API ou du frontend est teste par le code, sans restart reel apres
incident demontre sur la VM.

## 13. Securite et cadre reglementaire

Mesures deja presentes :

- authentification JWT locale, roles et isolation par organisation ;
- endpoint de sante public limite ;
- variables d'environnement et secrets GitHub pour la configuration de test ;
- separation des services Docker ;
- export explicite des donnees.

Points a renforcer pour une production reelle :

- remplacer les secrets de developpement par un gestionnaire de secrets ;
- renforcer l'authentification et la gestion des secrets pour une production reelle ;
- documenter la duree de conservation des avis ;
- anonymiser les auteurs si le contexte d'usage l'exige ;
- formaliser les contraintes RGPD.

## 14. Limites connues

- Le scraping Trustpilot depend de la structure HTML du site.
- L'ancienne tentative Showroomprive a recu HTTP 403 ; la collecte privee Vapoter demontre ensuite plus de 10 000 IDs sur les vues accessibles. Les metadonnees de profil sont une observation ponctuelle ; le nom juridique complet et les droits de republication des textes restent a documenter.
- Les avis ironiques ou tres courts restent difficiles a classer.
- La classe `Neutre` est plus difficile a apprendre.
- Les corrections humaines doivent rester coherentes pour ne pas degrader le modele.
- Le monitoring GitHub Actions concerne la VM de test, pas un SLA de production ; des evenements `schedule` sont prouves, mais pas encore une sonde planifiee active de la VM.
- Le deploiement automatise cible une VM scolaire existante, sans provisioning cloud.
- Le rollback DB/migrations n'a pas ete demontre.
- Le rollback applicatif a ete teste entre deux revisions Git dont la seconde
  est un commit vide ; le retour de fonctionnalites differentes n'est pas prouve.
- La v53 correspond au registre MLflow conserve ; un cold start sur registre
  vierge cree une nouvelle v1 et non une copie de cet historique.

## 15. Perspectives

Les evolutions les plus pertinentes sont :

1. documenter les droits de reutilisation et, si necessaire, le nom juridique de l'entreprise, puis etudier la representativite temporelle du corpus prive ;
2. enrichir le corpus avec plus d'entreprises et de secteurs ;
3. ajouter une classification thematique plus robuste ;
4. brancher d'autres sources d'avis via API ou CSV ;
5. verifier une sonde planifiee active avec le cron horaire deja retabli ;
6. preparer un eventuel provisioning cloud distinct de la VM scolaire ;
7. formaliser RGPD, retention et securite de production.

## 16. Conclusion technique

Le projet couvre les principales etapes attendues : collecte, organisation, traitement, machine learning, restitution, API, dockerisation et boucle d'amelioration. Il a evolue d'un pipeline de scraping vers une application produit exploitable par une entreprise pour analyser sa satisfaction client et prioriser ses actions.

# Architecture Decisions - Satisfaction Client

Ce fichier resume les decisions structurantes du projet. Il sert de reference rapide pour les prochains agents.

## ADR-001 - Positionnement SaaS B2B multi-clients

Statut : accepte.

Le projet n'est plus seulement un scraper Trustpilot. Il vise une application B2B multi-clients ou chaque organisation analyse ses propres avis.

Consequences :

- toutes les donnees metier doivent etre rattachees a une organisation ;
- l'interface doit parler "espace client" et "organisation" ;
- les futures integrations doivent respecter le multi-tenant ;
- les tests doivent verifier l'isolation des donnees.

## ADR-002 - React/Vite/TypeScript comme interface principale

Statut : accepte.

React/Vite/TypeScript est devenu le frontend produit.

Streamlit reste present pour l'historique et certaines demonstrations, mais il ne doit plus etre considere comme l'interface principale.

Consequences :

- les nouvelles experiences utilisateur doivent aller dans `frontend/` ;
- eviter d'ajouter de nouvelles pages Streamlit sauf demande explicite ;
- le frontend produit doit consommer l'API FastAPI.

## ADR-003 - FastAPI comme API produit

Statut : accepte.

FastAPI est retenu pour l'API produit malgre le contexte de cours mentionnant aussi Flask.

Raisons :

- schemas Pydantic ;
- documentation OpenAPI automatique ;
- async compatible ;
- integration simple avec React ;
- bonne separation entre API produit et scripts historiques.

Consequences :

- les nouveaux endpoints produit doivent etre dans `app/api/routes/` ;
- les schemas doivent etre dans `app/api/schemas.py` ;
- les tests API doivent etre ajoutes dans `tests/`.

## ADR-004 - PostgreSQL comme base produit

Statut : accepte.

PostgreSQL stocke organisations, utilisateurs, runs, avis, predictions, corrections, alertes et audit.

Consequences :

- ne pas stocker l'etat produit uniquement en fichiers CSV/JSON ;
- toujours tenir compte de l'organisation courante ;
- les scripts historiques peuvent encore produire des fichiers, mais l'app produit travaille avec PostgreSQL.

## ADR-005 - Schema idempotent au demarrage, pas Alembic

Statut : remplace par ADR-017.

Le schema initial est dans `init_db.sql`, puis `app/api/database.py` applique des creations et evolutions idempotentes au demarrage de l'API.

Raisons :

- vitesse de developpement ;
- simplicite Docker locale ;
- compatibilite avec la base deja existante de l'utilisateur.

Limites :

- moins robuste qu'un vrai systeme de migrations ;
- difficile a auditer en production ;
- a revisiter avant deploiement cloud.

## ADR-006 - Celery + Redis pour les traitements longs

Statut : accepte.

Les analyses et reentrainements ne doivent pas bloquer l'API HTTP. Celery execute ces traitements en arriere-plan et Redis sert de broker/backend.

Consequences :

- les endpoints creent ou declenchent un job ;
- le frontend suit les statuts de runs ;
- les erreurs worker doivent etre visibles via les statuts et events.

## ADR-007 - JWT local email/password

Statut : accepte pour le MVP.

L'auth utilise email/password, hash bcrypt et JWT signe.

Raisons :

- autonome en local ;
- simple a tester ;
- suffisant pour demo produit.

Limites :

- stockage frontend en `localStorage` ;
- pas de rotation avancee ;
- pas de MFA ;
- pas de SSO ;
- secrets de dev a remplacer en production.

## ADR-008 - Roles admin et member

Statut : accepte.

Deux roles existent actuellement :

- `admin` : peut modifier, inviter, lancer analyses, gerer alertes, corriger, reentrainer ;
- `member` : lecture et consultation, avec restrictions sur les actions sensibles.

Consequences :

- les routes sensibles doivent utiliser `require_org_admin` ;
- le frontend doit afficher un etat lecture seule aux membres ;
- les tests doivent couvrir les refus 403.

## ADR-009 - Trustpilot et CSV comme sources actives

Statut : accepte.

Trustpilot reste la source web publique active. CSV est la source B2B principale car elle permet d'analyser des exports clients sans dependance directe a une plateforme.

Consequences :

- ne pas redevenir URL-only ;
- documenter les formats CSV ;
- garder une abstraction de source pour ajouter de futurs connecteurs.

## ADR-010 - Connecteurs futurs en mode prepare

Statut : accepte.

Google Reviews, Zendesk, Shopify et support interne apparaissent comme sources preparees ou planifiees, mais ne doivent pas etre annoncees comme connecteurs fonctionnels tant que le code ne consomme pas vraiment leurs APIs.

Consequences :

- libelles frontend clairs ;
- documentation honnete ;
- tests ne doivent pas supposer des APIs externes actives.

## ADR-011 - scikit-learn + MLflow pour le modele

Statut : accepte.

Le modele de sentiment utilise scikit-learn et MLflow.

Raisons :

- explicable ;
- leger ;
- compatible petit corpus annote ;
- reproductible localement ;
- adapte au cadre pedagogique et produit MVP.

Alternatives considerees :

- LLM externe ;
- Hugging Face Transformers ;
- APIs NLP cloud.

Ces alternatives restent possibles plus tard, mais ne sont pas le choix actuel.

## ADR-012 - Corrections humaines comme boucle d'amelioration

Statut : accepte.

Les corrections d'avis sont stockees et reutilisees au reentrainement avec un poids plus fort que le corpus historique.

Consequences :

- les corrections doivent rester liees aux avis/runs/organisations ;
- l'interface doit permettre d'auditer les corrections ;
- le reentrainement ne doit pas etre lance sans contexte ou droit admin.

## ADR-013 - Action center et alertes comme valeur produit

Statut : accepte.

Le cockpit d'accueil et les alertes metier donnent une valeur immediate a l'utilisateur, au-dela du simple rapport analytique.

Consequences :

- les alertes doivent etre lisibles, actionnables et rattachees a un run ;
- les statuts d'alertes doivent etre persistants ;
- les membres peuvent consulter, mais les admins gerent les alertes.

## ADR-014 - Docker Compose comme runtime local de reference

Statut : accepte.

Docker Compose reste le moyen principal de lancer le produit localement.

Consequences :

- toute nouvelle dependance serveur doit etre compatible Docker ;
- documenter les commandes Docker ;
- la CI doit au minimum pouvoir construire l'image.

## ADR-015 - Garder les scripts historiques

Statut : accepte.

Les scripts historiques et le dashboard Streamlit ne sont pas supprimes.

Raisons :

- audit ;
- comparaison ;
- demonstration ;
- compatibilite avec l'historique de projet.

Consequences :

- ne pas casser `worker` sans raison ;
- documenter clairement que React/FastAPI est le produit principal.

## ADR-016 - Pas de commit automatique des modeles locaux

Statut : accepte.

Les entrainements locaux peuvent modifier `app/models/sentiment_model.pkl`. Ce fichier ne doit pas etre committe par reflexe.

Consequences :

- verifier `git status` apres chaque entrainement ;
- restaurer le fichier si la modification n'est pas intentionnelle ;
- privilegier MLflow pour tracer les versions modele.

## ADR-017 - Alembic pour le schema produit

Statut : accepte.

Le schema produit est versionne dans `migrations/versions/`. `init_db.sql` reste
limite aux tables historiques `dim_companies` et `fact_reviews`.

La premiere revision constitue une baseline compatible avec les bases locales
existantes. Une base non versionnee est inspectee avant d'etre marquee a la
revision courante. La baseline est refusee si une table, une colonne ou un index
produit attendu manque.

Consequences :

- l'API et Celery appliquent automatiquement les migrations au demarrage ;
- un verrou PostgreSQL empeche deux processus de migrer simultanement ;
- toute evolution du schema produit exige une nouvelle revision Alembic ;
- les tests couvrent base neuve, baseline sans perte et schema partiel ;
- un downgrade exige une confirmation explicite et une sauvegarde prealable.

## Decisions a revisiter

Ces decisions sont correctes pour le MVP, mais devront probablement evoluer avant un vrai deploiement SaaS :

- durcir l'auth ;
- externaliser les secrets ;
- ajouter monitoring et backups ;
- clarifier la strategie modele par organisation ;
- ajouter des tests frontend ;
- decomposer le frontend monolithique ;
- formaliser RGPD et retention.

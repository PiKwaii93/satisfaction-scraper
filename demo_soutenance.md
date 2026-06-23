# Scenario de soutenance - Satisfaction Client

Ce document sert de fil conducteur pour presenter le projet en soutenance. L'objectif est de montrer une solution concrete, pas seulement un scraper ou un modele : l'utilisateur peut analyser des avis, comprendre les irritants, corriger les erreurs, reentrainer le modele et exporter un rapport.

## 1. Objectif de la demo

Montrer en 8 a 12 minutes que le projet couvre toute la chaine attendue :

- collecte ou import d'avis clients ;
- stockage et historisation ;
- prediction de sentiment par un modele proprietaire ;
- restitution metier dans une application web ;
- correction humaine ;
- reentrainement suivi dans MLflow ;
- benchmark entre entreprises ;
- API, Docker et CI pour l'industrialisation.

## 2. Preparation avant soutenance

Depuis la racine du projet :

```powershell
cd C:\Users\Maxen\OneDrive\Documents\GitHub\satisfaction-scraper
```

Demarrer les services :

```powershell
docker-compose up -d postgres_db mlflow redis celery_worker api frontend
```

Verifier que l'API repond :

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Ouvrir les interfaces utiles :

- application React : <http://localhost:5173>
- documentation FastAPI : <http://localhost:8000/docs>
- MLflow : <http://localhost:5000>

Verifier le build frontend si besoin :

```powershell
npm --prefix frontend run build
```

Verifier les tests backend si besoin :

```powershell
docker-compose run --rm api sh -c "python -m pip install -r requirements-dev.txt && python -m pytest -q"
```

## 3. Parcours de demonstration recommande

### Etape 1 - Positionner le besoin

Message a faire passer :

> Une entreprise recoit des avis clients sur plusieurs canaux. Lire chaque avis a la main prend du temps. Le projet transforme ces avis en indicateurs : satisfaction globale, irritants, avis critiques, priorites et tendances comparables.

Points a montrer :

- le frontend React ;
- l'historique des analyses ;
- le fait que l'application raisonne par entreprise et par run d'analyse.

### Etape 2 - Lancer une analyse Trustpilot

Dans le panneau de gauche :

1. choisir la source `Trustpilot` ;
2. saisir une URL, par exemple :

```text
https://fr.trustpilot.com/review/www.boulanger.com
```

3. choisir `1` page par note pour une demo rapide ;
4. cliquer sur `Lancer l'analyse`.

Ce qu'il faut expliquer :

- l'API FastAPI cree un run ;
- Celery execute le travail en arriere-plan ;
- Redis sert de file de taches ;
- les resultats sont stockes dans PostgreSQL ;
- le journal d'execution evite que l'utilisateur soit dans le flou.

Plan B si le scraping est lent : ouvrir un run deja termine depuis l'historique.

### Etape 3 - Montrer l'import CSV

Dans le panneau de gauche :

1. choisir la source `CSV` ;
2. saisir une entreprise, par exemple `Entreprise Test CSV` ;
3. importer le fichier :

```text
data/test_import_reviews.csv
```

4. verifier le controle avant import ;
5. ajuster les colonnes si necessaire ;
6. cliquer sur `Importer le CSV`.

Ce qu'il faut expliquer :

- le produit ne depend pas uniquement de Trustpilot ;
- une entreprise peut fournir son propre export d'avis ;
- le mapping manuel rend l'import robuste aux noms de colonnes differents.

### Etape 4 - Lire le rapport entreprise

Sur un run termine, montrer :

- le nombre d'avis analyses ;
- la note moyenne ;
- la confiance IA ;
- la repartition des sentiments ;
- la repartition par note ;
- les irritants detectes ;
- les avis critiques ;
- les incoherences note / texte ;
- le score sante ;
- les priorites recommandees.

Message a faire passer :

> Le livrable n'est pas seulement une prediction de sentiment. C'est une aide a la decision pour prioriser les problemes clients.

### Etape 5 - Corriger des avis

Dans le tableau des avis :

1. changer de page si besoin ;
2. lire quelques verbatims ;
3. corriger un sentiment incoherent ;
4. montrer que la correction apparait dans la qualite IA.

Ce qu'il faut expliquer :

- le modele n'est pas considere parfait ;
- les erreurs deviennent des donnees utiles ;
- la boucle humaine permet d'ameliorer le corpus.

### Etape 6 - Reentrainer le modele

Dans le bloc `Entrainement IA` :

1. montrer le nombre de corrections pretes ;
2. cliquer sur `Reentrainer` ;
3. attendre la fin du run ;
4. montrer la nouvelle version de production ;
5. ouvrir MLflow si besoin.

Ce qu'il faut expliquer :

- le modele est entrainable depuis l'application ;
- les corrections humaines ont un poids plus fort ;
- MLflow garde l'historique des versions ;
- l'alias de production indique quelle version est utilisee.

### Etape 7 - Comparer plusieurs entreprises

Dans le benchmark :

1. selectionner deux a quatre runs termines ;
2. cliquer sur `Comparer` ;
3. montrer :

- l'entreprise la plus a risque ;
- le plus gros volume ;
- le sentiment commun principal ;
- les irritants communs ;
- les irritants propres ;
- l'export PDF.

Message a faire passer :

> La solution peut etre utilisee pour comparer plusieurs marques, magasins ou periodes d'analyse.

### Etape 8 - Montrer l'API et l'industrialisation

Ouvrir <http://localhost:8000/docs>.

Points a montrer :

- endpoints d'analyse ;
- endpoints d'import CSV ;
- endpoints de correction humaine ;
- endpoints de reentrainement ;
- securisation par cle API ;
- endpoint `/health`.

Puis expliquer rapidement :

- Docker Compose pour rendre le projet reproductible ;
- GitHub Actions pour verifier les PR ;
- tests backend et build frontend ;
- PostgreSQL pour l'historique ;
- MLflow pour le modele.

## 4. Commandes utiles pendant la demo

Voir les conteneurs :

```powershell
docker-compose ps
```

Suivre les logs API :

```powershell
docker-compose logs -f api
```

Suivre les logs Celery :

```powershell
docker-compose logs -f celery_worker
```

Verifier les runs en base :

```powershell
docker-compose exec postgres_db psql -U admin -d satisfaction_client -c "SELECT run_id, status, total_reviews, started_at, completed_at FROM analysis_runs ORDER BY run_id DESC LIMIT 10;"
```

Verifier le modele de production dans MLflow depuis l'application :

```text
http://localhost:5000
```

## 5. Plan B en cas d'imprevu

Si Trustpilot est lent ou bloque :

- utiliser un run deja termine dans l'historique ;
- faire une demo avec l'import CSV ;
- montrer le journal d'execution d'un ancien run ;
- ouvrir le rapport PDF exporte ;
- ouvrir MLflow pour prouver le suivi modele.

Si le frontend ne se recharge pas :

```powershell
docker-compose up -d --force-recreate frontend
```

Si l'API ou le worker ont besoin d'etre reconstruits :

```powershell
docker-compose up -d --build api celery_worker frontend
```

Si le modele MLflow ne semble pas a jour :

```powershell
docker-compose logs --tail=100 celery_worker
```

## 6. Questions probables du jury

### Pourquoi FastAPI plutot que Flask ?

FastAPI est adapte a une API produit moderne : validation automatique avec Pydantic, documentation Swagger native, bonne lisibilite des schemas et compatibilite avec les traitements asynchrones. Flask aurait aussi ete possible, mais FastAPI colle mieux a l'architecture API du projet.

### Pourquoi scikit-learn plutot qu'un LLM ?

La contrainte du projet est de construire un modele proprietaire. scikit-learn est explicable, leger, versionnable avec MLflow et suffisant pour un MVP sur corpus annote. Un modele Transformer pourrait etre une evolution future, mais il serait plus couteux et moins simple a justifier dans ce cadre.

### Pourquoi garder la note si on veut privilegier le texte ?

La note reste un signal utile, mais elle est ponderee. Le texte garde une influence centrale. Cela permet de gerer les cas ou la note et le verbatim ne racontent pas exactement la meme chose.

### Pourquoi ajouter l'import CSV ?

Le scraping n'est pas toujours possible ni souhaitable. L'import CSV rend la solution utilisable avec des exports clients, des donnees internes ou d'autres plateformes d'avis.

### Comment les corrections humaines ameliorent-elles le modele ?

Chaque correction est stockee en base. Lors du reentrainement, ces corrections sont reintegrees au dataset avec un poids plus eleve que les anciennes annotations. Elles rapprochent donc le modele des erreurs observees en conditions reelles.

### Quelles sont les limites actuelles ?

- classe `Neutre` plus difficile a apprendre ;
- ironie et avis tres courts difficiles ;
- dependance au HTML Trustpilot pour le scraping ;
- besoin de plus de secteurs et d'entreprises ;
- authentification et monitoring encore a industrialiser.

### Quelles sont les prochaines evolutions ?

- ajouter plus de tests automatises ;
- brancher d'autres sources d'avis ;
- renforcer la classification thematique ;
- ajouter une authentification utilisateur ;
- deployer une version cloud ;
- suivre les performances et la derive du modele.

## 7. Preuves a montrer dans le code

Fichiers utiles :

- `docker-compose.yml` : orchestration des services ;
- `app/api/main.py` : entree FastAPI ;
- `app/api/routes/analysis_runs.py` : endpoints d'analyse ;
- `app/api/routes/model_training.py` : endpoints de reentrainement ;
- `app/api/services/analysis_service.py` : logique metier des analyses ;
- `app/api/services/training_service.py` : logique de reentrainement ;
- `app/train_model.py` : pipeline ML historique et entrainement ;
- `frontend/src/App.tsx` : interface produit ;
- `tests/` : tests backend ;
- `.github/workflows/ci.yml` : pipeline CI ;
- `README.md` : installation et commandes ;
- `cahier_des_charges.md` : besoin et cadrage ;
- `rapport_technique.md` : architecture technique.

## 8. Conclusion a dire

> Le projet est parti d'un pipeline de scraping, puis a evolue vers une application produit. Aujourd'hui, une entreprise peut analyser des avis, identifier ses irritants, comparer plusieurs analyses, corriger les erreurs du modele et relancer un entrainement suivi dans MLflow. La solution reste un MVP, mais elle couvre deja les briques essentielles d'un produit data exploitable.

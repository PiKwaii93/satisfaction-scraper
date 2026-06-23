# Cahier des charges - Satisfaction Client

## 1. Presentation generale

### 1.1 Nom du projet

**Satisfaction Client**

### 1.2 Nature du projet

Satisfaction Client est une application Data / IA qui permet a une entreprise d'analyser ses avis clients. La solution collecte ou importe des avis, predit leur sentiment, detecte les irritants recurrents et produit une synthese exploitable par les equipes metier.

### 1.3 Contexte

En aval de la supply chain, les avis clients permettent de comprendre si le produit ou le service livre correspond aux attentes du marche. Les verbatims revelent souvent des problemes que les notes seules ne suffisent pas a expliquer : retards, remboursement, qualite produit, SAV, installation, prix ou disponibilite.

Lire ces avis manuellement est long et peu reproductible. Une solution data permet de traiter un volume plus important, de suivre des KPIs et de prioriser les actions correctives.

### 1.4 Problematique

Comment transformer des avis clients non structures en indicateurs de satisfaction fiables, actionnables et reutilisables pour ameliorer l'experience client ?

### 1.5 Objectifs

- Collecter des avis Trustpilot.
- Importer des avis depuis un CSV.
- Structurer les donnees dans PostgreSQL.
- Entrainer et exploiter un modele proprietaire de sentiment.
- Suivre les versions de modele avec MLflow.
- Restituer les resultats dans une interface web.
- Permettre la correction humaine et le reentrainement.
- Comparer plusieurs entreprises.
- Exporter des rapports et des jeux de donnees.

## 2. Utilisateurs cibles

| Utilisateur | Besoin principal | Valeur apportee |
| --- | --- | --- |
| Responsable service client | Identifier les avis critiques et themes recurrents. | Gagner du temps dans la priorisation. |
| Responsable supply chain | Detecter les problemes de livraison, delais et conformite. | Corriger les irritants operationnels. |
| Responsable experience client | Suivre la satisfaction globale. | Comprendre les forces et faiblesses perçues. |
| Analyste data | Disposer d'un historique propre et exportable. | Auditer les donnees et ameliorer le modele. |
| Direction | Avoir une synthese lisible. | Prendre des decisions rapides. |

## 3. Perimetre fonctionnel

### 3.1 Analyse Trustpilot

L'utilisateur peut saisir une entreprise ou une URL Trustpilot. L'application cree une analyse et recupere des avis par note et par page.

Fonctions attendues :

- validation de l'URL ;
- choix du nombre de pages par note ;
- lancement asynchrone ;
- journal d'execution ;
- detection des runs vides ou echoues ;
- relance possible.

### 3.2 Import CSV

L'utilisateur peut importer un fichier CSV contenant des avis clients.

Fonctions attendues :

- upload de fichier ;
- controle avant import ;
- detection des colonnes ;
- affichage du nombre d'avis exploitables ;
- apercu des premiers avis ;
- analyse identique aux runs Trustpilot.

### 3.3 Analyse de sentiment

Chaque avis est classe en :

- `Negatif` ;
- `Neutre` ;
- `Positif`.

Le modele doit privilegier le texte. La note client peut aider, mais ne doit pas remplacer l'analyse du verbatim.

### 3.4 Detection d'irritants

L'application doit detecter les principaux sujets operationnels :

- livraison ;
- delai ;
- SAV ;
- remboursement ;
- qualite produit ;
- prix ;
- retour ;
- installation.

Ces irritants servent a produire des priorites metier.

### 3.5 Rapport entreprise

Le rapport doit afficher :

- nombre d'avis analyses ;
- note moyenne ;
- confiance IA moyenne ;
- repartition des sentiments ;
- repartition par note ;
- irritants principaux ;
- avis critiques ;
- incoherences note / texte ;
- score sante ;
- priorites recommandees ;
- exports CSV et PDF.

### 3.6 Benchmark multi-entreprises

L'utilisateur peut selectionner plusieurs runs pour comparer des entreprises.

Le benchmark doit afficher :

- meilleur et moins bon score sante ;
- entreprise la plus negative ;
- entreprise avec le plus grand volume ;
- irritant commun ;
- irritants propres par entreprise ;
- tableau comparatif ;
- rapport PDF de benchmark.

### 3.7 Correction humaine

L'utilisateur peut corriger le sentiment predit d'un avis.

Fonctions attendues :

- choix du label corrige ;
- suppression d'une correction ;
- pagination des avis ;
- affichage complet des verbatims ;
- export CSV des corrections ;
- synthese qualite IA.

### 3.8 Reentrainement du modele

L'utilisateur peut lancer un reentrainement depuis l'interface.

Fonctions attendues :

- affichage du modele de production ;
- nombre de corrections disponibles ;
- lancement d'un run d'entrainement ;
- execution asynchrone ;
- suivi du statut ;
- metriques obtenues ;
- version MLflow produite.

## 4. Perimetre non fonctionnel

### 4.1 Reproductibilite

Le projet doit pouvoir etre lance localement avec Docker Compose.

### 4.2 Securite

Les endpoints metier doivent etre proteges par une cle API. Les secrets de developpement sont acceptables en local, mais devront etre externalises en production.

### 4.3 Performance

Les analyses longues doivent etre executees en arriere-plan pour ne pas bloquer l'interface.

### 4.4 Maintenabilite

Le code doit separer :

- API ;
- services metier ;
- taches asynchrones ;
- frontend ;
- scripts ML ;
- schema de base.

### 4.5 Traçabilite

Le systeme doit conserver :

- historique des analyses ;
- journal d'execution ;
- predictions ;
- corrections humaines ;
- versions de modele ;
- exports.

## 5. Donnees

### 5.1 Donnees entreprise

- nom ;
- slug ou source ;
- URL ;
- source (`trustpilot` ou `csv`) ;
- date de creation.

### 5.2 Donnees avis

- auteur ;
- note ;
- date brute ;
- date normalisee si disponible ;
- verbatim ;
- reponse entreprise ;
- entreprise ;
- run d'analyse.

### 5.3 Donnees prediction

- label predit ;
- score de confiance ;
- modele utilise ;
- date de prediction.

### 5.4 Donnees correction

- label predit ;
- label corrige ;
- commentaire optionnel ;
- date de correction.

### 5.5 Donnees entrainement

- corpus historique annote ;
- corrections humaines ;
- poids d'entrainement ;
- metriques ;
- version MLflow.

## 6. Architecture cible

```text
React frontend
    |
FastAPI
    |
PostgreSQL
    |
Celery + Redis
    |
Scraping Trustpilot / Import CSV
    |
Modele scikit-learn charge via MLflow
    |
Rapport, benchmark, corrections, reentrainement
```

Services Docker :

| Service | Role |
| --- | --- |
| `frontend` | Interface utilisateur React. |
| `api` | API FastAPI. |
| `celery_worker` | Traitements asynchrones. |
| `redis` | File de taches Celery. |
| `postgres_db` | Stockage relationnel. |
| `mlflow` | Registre de modele. |
| `worker` | Scripts Python historiques. |
| `dashboard` | Interface Streamlit historique. |

## 7. Modele IA

### 7.1 Approche retenue

Le modele repose sur scikit-learn afin de rester explicable, leger et facilement integrable a MLflow.

Il utilise :

- TF-IDF sur les verbatims ;
- signal de note client pondere ;
- classifieur multiclasses ;
- split train/test stratifie ;
- metriques par classe.

### 7.2 Evaluation attendue

- accuracy ;
- precision par classe ;
- recall par classe ;
- F1 par classe ;
- macro F1 ;
- weighted F1.

### 7.3 Boucle d'amelioration

Les corrections humaines sont integrees au dataset avec un poids superieur aux anciennes annotations, afin de rapprocher le modele des cas reels observes dans l'application.

## 8. Veille technologique

### 8.1 Solutions metier

| Solution | Interet | Limite |
| --- | --- | --- |
| Trustpilot Business | Gestion professionnelle des avis et analytics. | Solution fermee, modele non maitrise. |
| Google Business Profile / Google Reviews | Source d'avis tres large. | Acces API encadre, couverture differente selon les entreprises. |
| Avis Verifies | Solution specialisee e-commerce. | Donnees souvent moins ouvertes. |

### 8.2 Solutions IA / NLP

| Solution | Interet | Limite |
| --- | --- | --- |
| AWS Comprehend | Analyse de sentiment industrialisee. | Depend d'un service externe. |
| Google Cloud Natural Language | API NLP robuste. | Modele non proprietaire. |
| Hugging Face Transformers | Performance potentielle elevee. | Plus couteux et plus complexe a entrainer. |
| scikit-learn | Simple, explicable, compatible petit corpus. | Moins performant qu'un modele specialise large. |

### 8.3 Choix retenu

Le projet retient scikit-learn pour le MVP car la contrainte principale est de construire son propre modele, de maitriser les donnees et de garder une solution reproductible localement.

## 9. SWOT

### Forces

- Pipeline complet de bout en bout.
- Application web exploitable.
- API FastAPI.
- Traitement asynchrone.
- PostgreSQL et MLflow.
- Modele proprietaire.
- Boucle de correction humaine.
- Import CSV pour sortir de la dependance unique a Trustpilot.

### Faiblesses

- Corpus encore limite.
- Classe `Neutre` plus fragile.
- Scraping dependant de la structure Trustpilot.
- Monitoring encore simple.
- Pas d'authentification utilisateur complete.

### Opportunites

- Ajouter d'autres sources d'avis.
- Integrer Google Reviews via API si le cadre le permet.
- Ameliorer la classification thematique.
- Ajouter des tests automatises.
- Deployer une version cloud de demonstration.
- Ajouter des alertes metier.

### Menaces

- Changement HTML de Trustpilot.
- Contraintes legales autour du scraping.
- Donnees personnelles dans les avis.
- Biais si les corrections humaines sont incoherentes.
- Surapprentissage sur quelques entreprises.

## 10. Roadmap

| Phase | Objectif | Livrables |
| --- | --- | --- |
| 1. Cadrage | Comprendre le besoin et les KPIs. | Cahier des charges, personas, SWOT. |
| 2. Collecte | Recuperer des avis. | Scraper Trustpilot, import CSV, JSON/CSV d'exemple. |
| 3. Organisation | Structurer la donnee. | PostgreSQL, schema, pipeline. |
| 4. Analyse IA | Classer les sentiments. | Modele, metriques, MLflow. |
| 5. Produit | Restituer la valeur metier. | React, rapports, benchmark, exports. |
| 6. Amelioration | Corriger et reentrainer. | Feedback humain, reentrainement, suivi MLflow. |
| 7. Industrialisation | Renforcer exploitation. | CI, monitoring, auth, deploiement. |

## 11. Critieres de validation

Le projet est considere valide si :

- une analyse Trustpilot peut etre lancee ;
- un CSV peut etre importe ;
- les avis sont stockes en base ;
- le modele predit un sentiment ;
- les resultats sont visibles dans le frontend ;
- les avis sont exportables ;
- les corrections humaines sont stockees ;
- un reentrainement peut etre lance ;
- MLflow garde la version de production ;
- Docker Compose relance l'ensemble ;
- la documentation explique le besoin, l'architecture, les limites et la roadmap.

## 12. Limites et hypotheses

- Les avis publics peuvent contenir des donnees personnelles.
- Un usage production necessiterait une analyse RGPD plus formelle.
- Le scraping doit respecter les conditions des plateformes ciblees.
- Les exports CSV clients peuvent avoir des formats varies.
- Le modele aide a prioriser mais ne remplace pas l'analyse humaine sur les cas sensibles.

## 13. Conclusion

Satisfaction Client repond au besoin initial en proposant une solution concrete d'analyse d'avis clients. Le projet couvre les dimensions attendues : data collection, organisation de la donnee, machine learning, dashboard, API, dockerisation, amelioration continue et preparation a l'industrialisation.

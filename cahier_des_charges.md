# Cahier des Charges - Satisfaction Scraper

## 1. Présentation Générale

### 1.1 Nom du projet

**Satisfaction Scraper**

### 1.2 Nature du projet

Satisfaction Scraper est un projet Data / IA visant à collecter, structurer, analyser et visualiser des avis clients issus de plateformes publiques comme Trustpilot.

Le projet s'inscrit dans une problématique de satisfaction client en aval de la supply chain. Il cherche à transformer des verbatims clients non structurés en indicateurs exploitables pour aider une entreprise à mieux comprendre les causes de satisfaction ou d'insatisfaction.

### 1.3 Contexte métier

La supply chain regroupe l'ensemble des étapes d'approvisionnement, de production et de distribution d'un produit ou d'un service. En aval de cette chaîne, les avis clients permettent d'évaluer si l'expérience finale correspond aux attentes du marché.

Les avis clients peuvent révéler des problèmes liés à :

- la livraison ;
- la qualité ou la durabilité du produit ;
- le prix perçu ;
- le service client ;
- le remboursement ;
- la conformité du produit ;
- l'installation ;
- la disponibilité du service après-vente.

Cependant, lire manuellement un grand volume d'avis est long, fastidieux et difficilement reproductible. Les entreprises travaillent souvent par échantillonnage, ce qui peut faire passer à côté de signaux faibles importants.

### 1.4 Problématique

Comment automatiser la collecte et l'analyse des avis clients afin de synthétiser les feedbacks, détecter les irritants récurrents et aider à la redirection des clients insatisfaits ?

### 1.5 Finalité du projet

La finalité du projet est de produire une solution reproductible permettant de :

- récupérer automatiquement des avis clients ;
- stocker ces avis dans une base de données structurée ;
- entraîner un modèle propriétaire de classification de sentiment ;
- analyser les verbatims au-delà de la note numérique ;
- visualiser les résultats dans un dashboard ;
- tester la robustesse du modèle sur plusieurs entreprises ;
- préparer les bases d'une industrialisation future.

## 2. Why / What / Value

| Axe | Description |
| --- | --- |
| Why | Les avis clients contiennent des informations essentielles sur la satisfaction, mais ils sont difficiles à exploiter manuellement à grande échelle. |
| What | Construire un pipeline de scraping, stockage, classification de sentiment et visualisation des avis clients. |
| Value | Aider les équipes métier à identifier les problèmes prioritaires, suivre la satisfaction et améliorer l'expérience client. |

## 3. Objectifs du Projet

### 3.1 Objectifs métier

Le projet doit permettre de :

- mesurer la satisfaction client à partir de textes libres ;
- identifier rapidement les avis négatifs ou à risque ;
- synthétiser les feedbacks clients ;
- détecter les irritants liés à la supply chain ;
- analyser si le produit ou service correspond aux attentes du marché ;
- fournir des indicateurs exploitables aux équipes service client, marketing et supply chain.

### 3.2 Objectifs data

Le projet doit permettre de :

- constituer un corpus annoté de verbatims clients ;
- entraîner un modèle supervisé de classification de sentiment ;
- évaluer le modèle avec des métriques de classification ;
- comparer plusieurs modes de prédiction ;
- enrichir progressivement le modèle avec de nouvelles entreprises ;
- garder une traçabilité des données et des versions de modèle.

### 3.3 Objectifs techniques

Le projet doit permettre de :

- scraper des avis Trustpilot ;
- organiser les données dans PostgreSQL ;
- construire un pipeline ETL ;
- versionner le modèle avec MLflow ;
- dockeriser les services ;
- exposer un dashboard Streamlit ;
- préparer une future API de prédiction ;
- ouvrir la voie à une automatisation CI/CD.

## 4. Discovery et Recueil du Besoin

### 4.1 Interlocuteurs ciblés

Pour comprendre les besoins métier, les interlocuteurs suivants sont identifiés :

| Interlocuteur | Besoin principal | Valeur attendue |
| --- | --- | --- |
| Responsable supply chain | Identifier les irritants liés à la livraison, aux délais et à la conformité produit. | Prioriser les actions opérationnelles. |
| Responsable service client | Repérer les avis négatifs et les clients à recontacter. | Améliorer la réactivité et la satisfaction. |
| Responsable marketing / expérience client | Comprendre la perception globale de l'entreprise. | Identifier les forces et faiblesses perçues. |
| Analyste data | Disposer de données propres, traçables et exploitables. | Produire des analyses fiables et améliorer le modèle. |
| Direction métier | Suivre des indicateurs synthétiques de satisfaction. | Aider à la décision stratégique. |

### 4.2 Guide d'entretien proposé

Le guide d'entretien suivant peut être utilisé pour collecter les besoins :

1. Quels types d'avis clients consultez-vous actuellement ?
2. Quels problèmes souhaitez-vous repérer en priorité ?
3. Quels indicateurs utilisez-vous déjà pour mesurer la satisfaction ?
4. La note client suffit-elle à comprendre la satisfaction réelle ?
5. Quels verbatims doivent être considérés comme prioritaires ?
6. Quels thèmes sont les plus importants : livraison, SAV, prix, qualité, remboursement, durabilité ?
7. À quelle fréquence souhaitez-vous suivre les résultats ?
8. Quels formats de restitution sont les plus utiles : dashboard, export CSV, rapport, alerte ?
9. Quels sont les risques si un avis négatif important n'est pas détecté ?
10. Quelles contraintes réglementaires ou internes doivent être prises en compte ?

### 4.3 Besoins identifiés

Les besoins principaux sont :

- automatiser la collecte des avis ;
- éviter la lecture manuelle exhaustive ;
- identifier les avis négatifs ;
- comprendre les causes récurrentes d'insatisfaction ;
- visualiser la répartition des sentiments ;
- conserver un historique exploitable ;
- améliorer la fiabilité du modèle par itérations.

### 4.4 Experience map simplifiée

| Étape | Action utilisateur | Problème actuel | Réponse apportée par le projet |
| --- | --- | --- | --- |
| Collecte | L'utilisateur consulte plusieurs pages Trustpilot. | Lecture longue et non automatisée. | Scraping automatisé. |
| Analyse | L'utilisateur lit les avis un par un. | Analyse subjective et lente. | Classification de sentiment. |
| Priorisation | L'utilisateur cherche les avis critiques. | Les avis importants peuvent être manqués. | Filtrage par sentiment et score. |
| Reporting | L'utilisateur prépare une synthèse. | Travail manuel peu reproductible. | Dashboard et export CSV. |
| Amélioration | L'utilisateur veut suivre l'évolution. | Pas de boucle d'amélioration structurée. | Enrichissement du corpus et réentraînement. |

## 5. KPIs et Métriques de Suivi

### 5.1 KPIs métier

| KPI | Description | Intérêt métier |
| --- | --- | --- |
| Distribution des sentiments | Part d'avis positifs, neutres et négatifs. | Mesurer la perception globale. |
| Taux d'avis négatifs | Proportion d'avis classés négatifs. | Prioriser les actions correctives. |
| Répartition par note | Volume d'avis par nombre d'étoiles. | Comparer note déclarée et sentiment texte. |
| Taux de réponse entreprise | Part des avis auxquels l'entreprise répond. | Mesurer la réactivité perçue. |
| Volume d'avis par entreprise | Nombre d'avis collectés par cible. | Suivre la couverture de données. |

### 5.2 KPIs data et modèle

| KPI | Description | Objectif |
| --- | --- | --- |
| Accuracy | Taux global de bonnes prédictions. | Suivre la performance générale. |
| Precision par classe | Fiabilité des prédictions par sentiment. | Limiter les faux positifs. |
| Recall par classe | Capacité à retrouver chaque sentiment. | Ne pas manquer les avis négatifs. |
| F1-score par classe | Équilibre precision / recall. | Comparer les classes de façon robuste. |
| Macro F1 | Moyenne non pondérée des F1. | Surveiller la classe minoritaire `Neutre`. |

### 5.3 KPIs techniques et DevOps

| KPI | Description |
| --- | --- |
| Temps d'exécution du scraping | Durée nécessaire pour collecter un lot d'avis. |
| Taux d'échec du scraping | Nombre de pages ou avis non récupérés. |
| Fréquence de réentraînement | Nombre de versions du modèle produites. |
| Disponibilité du dashboard | Capacité à consulter les résultats localement. |
| Reproductibilité Docker | Capacité à relancer le projet sur une autre machine. |

## 6. Périmètre Fonctionnel

### 6.1 Collecte de données

Le système doit collecter deux niveaux de données.

Le premier niveau concerne les entreprises :

- nom de l'entreprise ;
- URL Trustpilot ;
- domaine ou thème ;
- nombre total d'avis ;
- TrustScore lorsque disponible ;
- pourcentage d'avis `Excellent` lorsque disponible.

Le second niveau concerne les avis :

- auteur ;
- note ;
- date ;
- verbatim ;
- entreprise associée ;
- réponse ou non de l'entreprise ;
- sentiment prédit ;
- score de confiance.

### 6.2 Organisation des données

Le système doit organiser les données dans une base PostgreSQL structurée.

Les tables principales sont :

- `dim_companies` : informations générales sur les entreprises ;
- `fact_reviews` : avis clients et résultats d'analyse.

Cette structure permet de séparer les données descriptives des entreprises et les avis individuels.

### 6.3 Analyse de sentiment

Le système doit classifier les avis en trois catégories :

- `Positif`
- `Neutre`
- `Négatif`

La classification doit privilégier le texte de l'avis. La note client peut être utilisée comme signal complémentaire, mais ne doit pas écraser le contenu textuel.

### 6.4 Dashboard

Le dashboard doit permettre :

- de consulter les avis collectés ;
- de visualiser la répartition des sentiments ;
- de visualiser la répartition des notes ;
- d'afficher le score de confiance ;
- d'inspecter les verbatims ;
- d'exporter les résultats en CSV.

### 6.5 Entraînement et amélioration du modèle

Le système doit permettre :

- de charger un corpus annoté ;
- d'entraîner un modèle supervisé ;
- d'afficher les métriques ;
- de sérialiser le modèle ;
- de publier le modèle dans MLflow ;
- de réutiliser le modèle pour prédire de nouveaux avis.

### 6.6 Tests externes

Le système doit permettre de tester une entreprise non présente dans le corpus initial afin d'évaluer la généralisation du modèle.

Les avis externes doivent pouvoir être :

- scrapés ;
- prédits ;
- chargés dans le dashboard ;
- exportés ;
- audités ;
- éventuellement annotés puis intégrés au corpus.

## 7. Hors Périmètre du MVP

Les éléments suivants ne font pas partie du MVP actuel :

- authentification utilisateur ;
- interface d'administration complète ;
- interface web collaborative d'annotation ;
- alertes automatiques en temps réel ;
- déploiement cloud public ;
- monitoring Prometheus/Grafana complet ;
- API publique de prédiction ;
- classification thématique fine par cause métier.

Ces éléments sont toutefois envisagés comme évolutions possibles.

## 8. Données Utilisées

### 8.1 Sources

La source principale est Trustpilot.

Les entreprises déjà utilisées dans le projet incluent :

- Showroomprivé ;
- La Bonne Allure ;
- Decathlon ;
- Intersport ;
- Cdiscount ;
- Darty.

### 8.2 Données historiques

Le projet s'appuie sur des avis historiques stockés dans :

```text
data/showroom_reviews.json
```

Ces données constituent la base initiale d'analyse et d'entraînement.

### 8.3 Données d'annotation

Le corpus d'entraînement consolidé est stocké dans :

```text
annotations_training.csv
```

Les colonnes attendues sont :

- `id`
- `verbatim`
- `rating`
- `manual_label`
- `label_confidence`
- `issue_type`
- `is_mixed`
- `justification_courte`

### 8.4 Données externes

Les avis externes sont stockés dans :

```text
data/external/
```

Ce dossier contient :

- des fichiers JSON d'avis scrapés ;
- des CSV de prédictions ;
- des CSV annotés ;
- des fichiers d'exclusion pour les cas trop ambigus.

## 9. Discovery Technique et Qualité des Données

### 9.1 Types de données

Le projet manipule :

- données textuelles : verbatims ;
- données numériques : notes, scores, volumes ;
- données catégorielles : labels, entreprises, thèmes ;
- données temporelles : dates d'avis ;
- données booléennes : réponse entreprise, avis mixte.

### 9.2 Difficultés identifiées

Les principales difficultés sont :

- avis vides ;
- avis très courts ;
- ironie ;
- fautes d'orthographe ;
- mélange de positif et négatif ;
- discordance entre note et texte ;
- négations ambiguës ;
- évolution possible du HTML Trustpilot.

### 9.3 Analyses de données prévues

Les analyses prévues sont :

- distribution des notes ;
- distribution des labels ;
- comparaison note / sentiment ;
- audit des cas à faible confiance ;
- analyse des erreurs de classification ;
- comparaison entre entreprises ;
- comparaison texte seul / texte + note.

## 10. Architecture Technique

### 10.1 Architecture globale

```text
Trustpilot
    |
    v
Scraping Playwright
    |
    v
Fichiers JSON / CSV
    |
    v
Pipeline ETL Python
    |
    v
PostgreSQL
    |
    v
Dashboard Streamlit

Annotations CSV
    |
    v
Entraînement scikit-learn
    |
    v
Modèle sérialisé + MLflow
    |
    v
Prédiction de nouveaux avis
```

### 10.2 Services Docker

Le projet utilise Docker Compose avec les services suivants :

| Service | Rôle |
| --- | --- |
| `postgres_db` | Stockage relationnel des entreprises et avis. |
| `mlflow` | Suivi des expériences et registre du modèle. |
| `worker` | Exécution des scripts Python. |
| `dashboard` | Interface Streamlit. |

### 10.3 Technologies

| Besoin | Technologie |
| --- | --- |
| Scraping | Playwright |
| Traitement de données | Pandas |
| Machine Learning | scikit-learn |
| Versioning modèle | MLflow |
| Base de données | PostgreSQL |
| Dashboard | Streamlit |
| Conteneurisation | Docker Compose |
| Versioning code | Git / GitHub |

## 11. Schéma de Base de Données

### 11.1 Table `dim_companies`

Cette table stocke les informations générales des entreprises.

Champs principaux :

- `company_id`
- `company_name`
- `company_url`
- `theme`
- `total_reviews_count`
- `trustscore`
- `pct_excellent_reviews`

### 11.2 Table `fact_reviews`

Cette table stocke les avis clients.

Champs principaux :

- `review_id`
- `company_id`
- `author_name`
- `rating`
- `review_date`
- `verbatim`
- `company_responded`
- `sentiment_label`
- `sentiment_score`

### 11.3 Évolutions possibles du schéma

Des tables complémentaires pourront être ajoutées :

- `dim_topics` : thèmes d'insatisfaction ;
- `fact_predictions` : historique des prédictions par version de modèle ;
- `dim_model_versions` : suivi des versions MLflow ;
- `fact_alerts` : avis nécessitant une action prioritaire.

## 12. Pipeline de Traitement

### 12.1 Extraction

Le scraping récupère les avis Trustpilot selon :

- l'entreprise ciblée ;
- les notes souhaitées ;
- le nombre de pages par note.

### 12.2 Transformation

Les traitements incluent :

- nettoyage du texte ;
- normalisation des notes ;
- gestion des dates ;
- suppression ou signalement des avis vides ;
- prédiction du sentiment ;
- calcul du score de confiance.

### 12.3 Chargement

Les données transformées sont chargées dans PostgreSQL.

Le dashboard consomme ensuite directement les données stockées en base.

### 12.4 Boucle d'amélioration

Le pipeline prévoit une boucle d'amélioration continue :

1. tester le modèle sur une nouvelle entreprise ;
2. exporter les résultats ;
3. auditer les incohérences ;
4. annoter les cas utiles ;
5. enrichir le corpus ;
6. réentraîner le modèle ;
7. comparer les performances.

## 13. Modèle de Sentiment

### 13.1 Approche retenue

Le modèle actuel repose sur scikit-learn :

- vectorisation TF-IDF des verbatims ;
- encodage de la note client ;
- régression logistique multiclasses ;
- pondération équilibrée des classes.

La note client est utilisée comme signal auxiliaire, avec une pondération réduite :

```text
RATING_FEATURE_WEIGHT = 0.25
```

### 13.2 Vérité terrain

La vérité terrain est fournie par la colonne :

```text
manual_label
```

Les labels possibles sont :

- `Négatif`
- `Neutre`
- `Positif`

### 13.3 Évaluation

Le modèle doit afficher :

- accuracy ;
- precision par classe ;
- recall par classe ;
- F1-score par classe ;
- macro average ;
- weighted average.

### 13.4 Garde-fous métier

Des règles complémentaires sont appliquées après la prédiction pour éviter des incohérences évidentes.

Exemples :

- "je suis déçu de mon achat" doit être classé négatif ;
- "jamais déçue" doit pouvoir être classé positif ;
- un avis 1 ou 2 étoiles ne doit pas être positif sans signal très fort ;
- un problème résolu dans un avis bien noté peut rester positif.

## 14. MVP

### 14.1 Fonctionnalités incluses

Le MVP comprend :

- scraping Trustpilot ;
- stockage PostgreSQL ;
- dashboard Streamlit ;
- modèle de sentiment supervisé ;
- suivi MLflow ;
- test d'entreprises externes ;
- export CSV ;
- documentation des commandes.

### 14.2 Fonctionnalités exclues du MVP

Sont exclues du MVP :

- API publique ;
- système d'alertes ;
- authentification ;
- interface d'annotation complète ;
- déploiement cloud ;
- monitoring avancé.

### 14.3 Justification du MVP

Le MVP se concentre sur la valeur principale : transformer des avis clients non structurés en indicateurs exploitables. Les fonctionnalités avancées sont repoussées afin de garantir un pipeline data fonctionnel, démontrable et améliorable.

## 15. API et Mise en Production Future

### 15.1 API prévue

Une API pourra être développée dans une phase ultérieure afin de :

- tester le modèle sur un avis fourni en entrée ;
- requêter les avis historiques ;
- exposer les prédictions à une application tierce ;
- automatiser l'intégration avec d'autres outils.

Technologies possibles :

- FastAPI ;
- Flask.

### 15.2 Exemple d'endpoint futur

```text
POST /predict
```

Entrée :

```json
{
  "verbatim": "Livraison rapide et produit conforme",
  "rating": 5
}
```

Sortie :

```json
{
  "sentiment_label": "Positif",
  "sentiment_score": 0.89
}
```

### 15.3 Dockerisation

L'ensemble du projet doit rester dockerisé afin d'être reproductible sur une autre machine.

## 16. DevOps, Déploiement et Monitoring

### 16.1 Versioning

Le code est versionné avec Git et hébergé sur GitHub.

Les éléments versionnés incluent :

- scripts de scraping ;
- scripts ETL ;
- scripts ML ;
- dashboard ;
- fichiers d'annotation ;
- documentation.

### 16.2 CI/CD futur

Une automatisation GitHub Actions pourra être mise en place pour :

- vérifier la qualité du code ;
- lancer des tests unitaires ;
- construire l'image Docker ;
- vérifier le démarrage des services ;
- publier les artefacts nécessaires.

### 16.3 Monitoring futur

Des outils comme Prometheus et Grafana pourraient être ajoutés afin de suivre :

- disponibilité des services ;
- durée du scraping ;
- erreurs d'ETL ;
- fréquence de prédiction ;
- dérive des distributions de sentiment ;
- succès ou échec des déploiements.

### 16.4 KPIs DevOps possibles

- Deployment frequency ;
- Deployment success rate ;
- Mean time to recovery ;
- durée moyenne du pipeline ;
- taux d'erreur du scraping.

## 17. Contraintes Réglementaires, Sécurité et RSE

### 17.1 RGPD

Les avis publics peuvent contenir des informations personnelles.

Le projet doit donc respecter les principes suivants :

- minimiser les données collectées ;
- ne pas collecter de données sensibles inutiles ;
- anonymiser les auteurs si nécessaire ;
- limiter l'usage au cadre pédagogique ou analytique ;
- documenter les sources de données.

### 17.2 Sécurité

En environnement local, les identifiants PostgreSQL sont visibles dans Docker Compose. En production, ils devront être déplacés vers :

- variables d'environnement ;
- secrets manager ;
- fichiers `.env` non versionnés.

### 17.3 Accessibilité et inclusion

Le dashboard devra rester lisible et compréhensible pour des profils techniques et non techniques.

Les visualisations devront éviter une dépendance exclusive aux couleurs et privilégier des libellés explicites.

### 17.4 RSE

La solution doit éviter des traitements excessifs inutiles :

- scraping ciblé plutôt que massif ;
- réutilisation des fichiers existants quand possible ;
- limitation des réentraînements inutiles ;
- conteneurisation reproductible pour éviter les installations lourdes.

## 18. Veille Technologique et Benchmark

### 18.1 Solutions métier

| Solution | Description | Pertinence |
| --- | --- | --- |
| Trustpilot Business | Plateforme d'analyse et gestion d'avis. | Très pertinente comme source d'inspiration, mais solution fermée. |
| Google Reviews / Business Profile | Avis clients associés aux établissements. | Pertinent pour élargir les sources, mais accès et structure différents. |
| Avis Vérifiés | Solution spécialisée dans la collecte d'avis. | Pertinent métier, mais moins adapté au scraping public. |

### 18.2 Produits digitaux et BI

| Solution | Description | Pertinence |
| --- | --- | --- |
| Power BI | Dashboarding métier. | Pertinent pour la restitution, pas pour le modèle. |
| Tableau | Visualisation avancée. | Pertinent pour BI, mais pas pour scraping/ML. |
| Looker Studio | Dashboard web. | Pertinent pour reporting léger. |

### 18.3 Solutions IA / NLP

| Solution | Description | Pertinence |
| --- | --- | --- |
| AWS Comprehend | Analyse de sentiment cloud. | Puissant, mais modèle non maîtrisé. |
| Google Cloud Natural Language | API NLP cloud. | Utile comme benchmark, mais dépendance externe. |
| Hugging Face Transformers | Modèles NLP open source. | Très pertinent pour une évolution future. |

### 18.4 Choix retenu

Le projet retient scikit-learn pour le MVP car :

- il est explicable ;
- il est léger ;
- il fonctionne bien avec un corpus annoté modéré ;
- il s'intègre facilement à MLflow ;
- il répond à la contrainte de construire son propre modèle.

## 19. Analyse SWOT

### 19.1 Forces

- Pipeline complet de bout en bout.
- Données centralisées dans PostgreSQL.
- Modèle propriétaire entraîné sur annotations.
- Dockerisation du projet.
- Dashboard exploitable par des profils métier.
- MLflow pour suivre les versions de modèle.

### 19.2 Faiblesses

- Corpus annoté encore limité.
- Classe `Neutre` difficile à apprendre.
- Dépendance au HTML de Trustpilot.
- Règles métier encore partiellement manuelles.
- Pas encore d'API ni CI/CD complet.

### 19.3 Opportunités

- Ajouter une classification thématique.
- Tester davantage d'entreprises.
- Intégrer des modèles Transformers.
- Déployer une API.
- Mettre en place des alertes sur avis négatifs.
- Ajouter du monitoring.

### 19.4 Menaces

- Changement de structure Trustpilot.
- Données ambiguës ou ironiques.
- Surapprentissage sur certaines entreprises.
- Contraintes RGPD en cas d'usage hors cadre pédagogique.
- Coût d'industrialisation si le volume augmente.

## 20. Risques et Limites

### 20.1 Risques techniques

- échec du scraping ;
- indisponibilité de PostgreSQL ;
- indisponibilité de MLflow ;
- problèmes de volumes Docker ;
- changement de structure des pages Trustpilot.

### 20.2 Risques modèle

- confusion entre avis neutres et avis mixtes ;
- influence excessive de certains mots-clés ;
- difficulté à détecter l'ironie ;
- besoin d'annotations supplémentaires ;
- performances variables selon le secteur d'activité.

### 20.3 Limites métier

Le modèle ne remplace pas l'analyse humaine sur les avis sensibles. Il sert à prioriser, synthétiser et accélérer l'analyse.

## 21. Livrables Attendus

### 21.1 Livrables actuels

1. Pipeline de scraping.
2. Fichiers JSON d'exemple.
3. Base PostgreSQL.
4. Pipeline ETL.
5. Modèle ML fonctionnel.
6. Dashboard Streamlit.
7. MLflow pour le versioning du modèle.
8. Corpus d'entraînement annoté.
9. Fichiers de validation externe.
10. README.
11. Cahier des charges.

### 21.2 Livrables futurs

1. API de prédiction.
2. Classification thématique.
3. CI/CD GitHub Actions.
4. Monitoring.
5. Documentation de déploiement.
6. Rapport final.
7. Support de soutenance.

## 22. Roadmap

| Phase | Objectif | Livrables | Ressources |
| --- | --- | --- | --- |
| 1. Cadrage | Comprendre le besoin et définir les KPIs. | Cahier des charges, guide d'entretien, SWOT. | Data analyst, interlocuteurs métier. |
| 2. Collecte | Scraper les avis et métadonnées entreprise. | JSON d'exemple, scripts scraping. | Python, Playwright. |
| 3. Organisation | Structurer les données en base. | Schéma PostgreSQL, pipeline ETL. | PostgreSQL, Pandas. |
| 4. Consommation | Produire modèle et dashboard. | Modèle ML, MLflow, dashboard. | scikit-learn, Streamlit. |
| 5. Validation | Tester sur entreprises externes. | CSV de prédictions, audits, annotations. | Corpus externe, analyse manuelle. |
| 6. Mise en production future | Exposer le modèle et automatiser. | API, Docker, CI/CD. | FastAPI, GitHub Actions. |
| 7. Monitoring futur | Suivre la qualité et la disponibilité. | Tableaux de bord techniques. | Prometheus, Grafana. |

## 23. Critères de Validation du Projet

Le projet sera considéré comme validé si :

- un fichier JSON d'avis est généré par scraping ;
- les avis sont chargés dans PostgreSQL ;
- un schéma de base est documenté ;
- un modèle ML est entraîné et évalué ;
- MLflow trace les versions du modèle ;
- le dashboard affiche les résultats ;
- Docker permet de relancer le projet ;
- des avis externes peuvent être testés ;
- les KPIs métier et techniques sont documentés ;
- les limites et perspectives sont clairement identifiées.

## 24. Conclusion

Satisfaction Scraper répond à la problématique initiale du projet : exploiter les verbatims clients pour mesurer la satisfaction et détecter les irritants opérationnels.

Le projet couvre les étapes attendues : collecte de données, organisation, consommation via ML et dashboard, dockerisation, et préparation d'une industrialisation future.

La solution apporte une première réponse concrète au besoin métier tout en gardant une trajectoire d'amélioration claire : enrichissement du corpus, classification thématique, API, automatisation CI/CD et monitoring.

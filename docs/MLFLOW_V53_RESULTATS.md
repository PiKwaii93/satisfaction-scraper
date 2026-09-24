# Résultats et preuves MLflow - modèle de sentiment v53

**Provenance.** Registre MLflow local conservé et volume d'artefacts consultés en lecture seule le **24 septembre 2026 à 06:36:44 UTC**. Les [exports assainis](../deliverables/mlflow_v53_evidence/README.md) et leur [manifeste d'empreintes](../deliverables/mlflow_v53_evidence/MANIFEST.json) accompagnent ce document. Les originaux sont gardés séparément dans une sauvegarde privée ; aucune capture d'interface n'est présentée comme existante.

## Version, run et protocole

Le modèle enregistré est `sentiment_model` **v53**, statut `READY`, URI immuable `models:/sentiment_model/53`. Son run `de7104ef534541309c8b8e6eecbb6755` est `FINISHED`. À la consultation, l'alias `production` pointait vers v53 et la v52 existait toujours avec statut `READY`. L'alias est un constat daté, pas une garantie de son état futur.

Le [code d'entraînement](../app/train_model.py) utilise TF-IDF sur le verbatim, la note pondérée (`rating_feature_weight=0.25`) et une régression logistique. La déduplication sur `normalized_verbatim+normalized_rating` intervient **avant** le split stratifié. Le run enregistre `random_state=42`, `test_size=0.2`, une pondération des corrections humaines de `6.0`, et la stratégie `stratified_after_global_deduplication`. La pondération est appliquée après la déduplication, comme poids d'échantillon ; elle ne repose pas sur des copies de lignes. La [preuve de séparation](../tests/test_ml_evaluation_split.py) vérifie notamment l'absence d'intersection selon cette clé et la reproductibilité. Le run seul ne permet pas de revérifier cette propriété sur le snapshot non exporté.

| Corpus et séparation | Effectif |
| --- | ---: |
| Avant déduplication | 1 656 |
| Après déduplication | 1 554 |
| Doublons retirés / groupes | 102 / 42 |
| Train / test | 1 243 / 311 |

| Classe | Corpus après déduplication | Train | Test |
| --- | ---: | ---: | ---: |
| Négatif | 715 | 572 | 143 |
| Neutre | 137 | 110 | 27 |
| Positif | 702 | 561 | 141 |

Sources enregistrées : `manual_annotations,review_feedback`. Nom du snapshot déclaré : `sentiment_training_dataset.csv`. Empreinte **enregistrée** du dataset, concordante entre paramètre du run et résumé d'artefact : `deb2f21da31b6c64c999fd539b79192e26d2fd1c71e820f31884294c0e9984cd`. Le contenu du snapshot n'a pas été exporté ni réhaché indépendamment pour ce dossier.

## Évaluation sur les 311 avis de test

| Métrique globale | Valeur exacte du run | Arrondi de présentation |
| --- | ---: | ---: |
| Accuracy | 0,842443729903537 | 0,842444 |
| Macro-F1 | 0,7458597156106053 | 0,745860 |
| Weighted-F1 | 0,858161640170085 | 0,858162 |

| Classe | Précision | Rappel | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| Négatif | 0,942149 | 0,797203 | 0,863636 | 143 |
| Neutre | 0,340000 | 0,629630 | 0,441558 | 27 |
| Positif | 0,935714 | 0,929078 | 0,932384 | 141 |

Matrice de confusion ; **lignes = classe réelle, colonnes = prédiction** :

| Réel / prédit | Négatif | Neutre | Positif |
| --- | ---: | ---: | ---: |
| Négatif | 114 | 26 | 3 |
| Neutre | 4 | 17 | 6 |
| Positif | 3 | 7 | 131 |

La diagonale totalise **262/311**, soit l'accuracy du run. Les précisions, rappels et F1 recalculés à partir de la matrice concordent avec le classification report et les métriques enregistrées. La classe **Neutre** est rare (137/1 554 ; support test 27) et son F1 de **0,441558** reste la limite principale. Le modèle est une référence méthodologiquement corrigée pour ce MVP ; ces preuves ne démontrent ni modèle optimal ni recherche exhaustive d'hyperparamètres.

## Ce que MLflow prouve, et ce qu'il ne prouve pas

Le registre associe la version au run, et le run conserve paramètres, métriques et trois artefacts vérifiés : `dataset/dataset_info.json`, `evaluation/classification_report.json`, `evaluation/confusion_matrix.json`. Leur nom et leurs empreintes figurent dans le [manifeste](../deliverables/mlflow_v53_evidence/MANIFEST.json). La distribution des classes est enregistrée comme métriques, sans artefact autonome identifié. La présence de l'artefact du modèle a été vérifiée, mais son binaire n'a pas été exporté dans ce dossier.

Le tag `production_alias_promotion_status=not_attempted` décrit **l'entraînement initial de la candidate**. L'alias `production` pointant ensuite vers v53 résulte d'une promotion ultérieure, constatée dans le registre ; il ne faut pas lire le tag comme l'état courant de l'alias.

La v53 et la v52 appartiennent au **registre conservé**. Lors d'un cold start sur un **registre vierge**, le bootstrap du pickle versionné crée une nouvelle **v1**, sans reproduire l'historique ni les métriques de v53. Ces deux registres ne doivent pas être confondus.

**Limites des preuves :** pas de capture authentique de l'interface ; pas de réhachage indépendant du contenu du snapshot ; pas de preuve nouvelle du chargement de l'alias par l'application ou de la synchronisation PostgreSQL ; pas de comparaison exhaustive des algorithmes. Les exports assainis prouvent l'état du registre **à la date de consultation** et les valeurs de ce run précis.

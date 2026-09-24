# État des preuves MLflow - registre conservé, modèle v53

Le registre local conservé et son volume d'artefacts ont été consultés **en lecture seule le 24 septembre 2026 à 06:36:44 UTC**. Les neuf exports originaux du dossier temporaire ont été copiés sans modification vers une sauvegarde privée hors Git, avec comparaison de leurs SHA-256. Ils ne doivent pas être publiés directement. Le [document de résultats](MLFLOW_V53_RESULTATS.md), le [PDF académique](../deliverables/08_Preuve_MLflow_v53.pdf) et les [copies assainies](../deliverables/mlflow_v53_evidence/README.md) sont **préparés pour validation**, sans commit ni push.

| Preuve demandée | Constat sur le registre | Pièce préparée / limite |
| --- | --- | --- |
| Modèle et version | `sentiment_model` v53, `READY`, URI `models:/sentiment_model/53` ; v52 toujours `READY`. | [summary.json](../deliverables/mlflow_v53_evidence/summary.json) ; constat daté, sans capture UI. |
| Run associé | `de7104ef534541309c8b8e6eecbb6755`, `FINISHED`. | Même résumé ; run unique pour toutes les valeurs ci-dessous. |
| Alias | `production` vers v53 à la consultation. | Extrait du registre dans le résumé ; ne prouve pas une surveillance continue de l'alias. |
| Corpus | SHA-256 enregistré `deb2f21da31b6c64c999fd539b79192e26d2fd1c71e820f31884294c0e9984cd` ; 1 656 lignes avant et 1 554 après déduplication, 102 retirées ; 1 243 train et 311 test. | Paramètre du run et [dataset_info.json](../deliverables/mlflow_v53_evidence/dataset_info.json) concordants. Chemin privé du snapshot retiré ; contenu non réhaché indépendamment. |
| Méthode et distribution | Clé verbatim + note normalisés, split stratifié après déduplication, `random_state=42`, `test_size=0.2`, feedback ×6 ; comptes de classes dans les métriques. | [summary.json](../deliverables/mlflow_v53_evidence/summary.json) ; pas d'artefact autonome de distribution identifié. |
| Métriques globales | Accuracy `0,842443729903537`, macro-F1 `0,7458597156106053`, weighted-F1 `0,858161640170085`. | Run et [classification_report.json](../deliverables/mlflow_v53_evidence/classification_report.json) concordants. |
| Métriques par classe et support | Négatif, Neutre, Positif avec précision, rappel, F1 et support. | Run et classification report ; valeurs détaillées dans les [résultats](MLFLOW_V53_RESULTATS.md). |
| Matrice de confusion | `[[114,26,3],[4,17,6],[3,7,131]]` dans l'ordre Négatif, Neutre, Positif. | [confusion_matrix.json](../deliverables/mlflow_v53_evidence/confusion_matrix.json) ; 262 bonnes prédictions sur 311. |
| Artefacts réellement enregistrés | `dataset/dataset_info.json`, `evaluation/classification_report.json`, `evaluation/confusion_matrix.json`. | Noms et empreintes de l'artefact du registre, de l'export privé et des copies assainies dans le [manifeste](../deliverables/mlflow_v53_evidence/MANIFEST.json). Le binaire du modèle n'a pas été exporté. |

Le tag du run `production_alias_promotion_status=not_attempted` décrit l'entraînement candidat initial. L'alias courant constaté sur v53 provient de la promotion ultérieure : ces deux éléments ne se contredisent pas.

**Preuves encore absentes :** captures authentiques de l'interface MLflow ; réhachage indépendant du snapshot ; nouvelle preuve de chargement de l'alias par l'application et de synchronisation des prédictions PostgreSQL. Le PDF repose sur les exports du registre, sans inventer de captures. Le **registre conservé v53** ne doit pas être confondu avec un **cold start sur registre vierge**, où le pickle bootstrap est enregistré comme nouvelle v1 sans l'historique v52-v53.

Aucun réentraînement, changement d'alias, écriture MLflow/PostgreSQL ni accès à la VM n'est nécessaire pour constituer ce dossier.

# Checklist de preuves MLflow — registre conservé, modèle v53

Préparation documentaire uniquement, au 22 septembre 2026. **Ne pas réentraîner, enregistrer une nouvelle version, changer d'alias ou synchroniser PostgreSQL pour constituer cette checklist.** Les données ci-dessous sont celles rapportées lors de la validation ML ; les captures/export du registre réel doivent permettre au jury de les contrôler.

| Pièce à capturer ou exporter depuis le registre réel | Valeur / point à vérifier | État de la preuve dans Git |
| --- | --- | --- |
| Fiche du modèle enregistré et de sa version | `sentiment_model` **v53**, statut READY, URI immuable `models:/sentiment_model/53`. | Version rapportée dans [TRACEABILITY.md](TRACEABILITY.md) ; capture de registre à exporter. |
| Fiche du run associé à v53 | `de7104ef534541309c8b8e6eecbb6755`. | Identifiant rapporté ; capture/lien de run à exporter. |
| Alias du registre | `production` pointant vers v53 ; conserver la preuve que v52 existe toujours. | Promotion validée dans l'historique du projet ; capture actuelle à exporter. |
| Traçabilité du corpus | `dataset_sha256 = deb2f21da31b6c64c999fd539b79192e26d2fd1c71e820f31884294c0e9984cd` ; lignes avant/après déduplication, source/snapshot et répartition par classe. | Hash rapporté ; comparer aux paramètres/tags/artefacts du run avant présentation. Le snapshot exact est local et exclu de Git. |
| Métriques globales | Accuracy `0,842444`, macro-F1 `0,745860`, weighted-F1 `0,858162` ; tailles train/test, `random_state=42`, `test_size`, doublons supprimés et stratégie de split. | Valeurs globales rapportées ; exporter les valeurs exactes du run. |
| Métriques par classe | Précision, rappel, F1 et support pour `Négatif`, `Neutre`, `Positif`. | Ne pas recopier de valeurs non relues dans le run ; exporter la table exacte. |
| Artefacts d'évaluation | Matrice de confusion, `classification_report`, description/empreinte du dataset et éventuels fichiers de répartition. | Télécharger ou capturer chaque artefact effectivement présent ; ne pas inventer un nom de fichier absent. |
| Cohérence application | URI `models:/sentiment_model@production` résolue vers v53 ; prédictions historisées après promotion si preuve disponible. | Distinguer lecture du registre, chargement applicatif et synchronisation DB. Aucune opération nouvelle demandée ici. |

**Deux scénarios à ne pas mélanger :** sur le registre **conservé**, la version de production validée est v53. Sur un **cold start avec registre MLflow vierge**, `model_bootstrap` enregistre le pickle versionné comme première version (v1 dans ce registre neuf) ; il ne recrée pas l'historique v1–v53. La comparaison des deux scénarios doit préciser le registre et les volumes utilisés. Les métriques de la v53 ne sont pas celles d'un nouveau run de bootstrap.

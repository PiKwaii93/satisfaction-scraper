# Preuves MLflow v53 - export assaini

Ces fichiers assainis publiés proviennent du registre MLflow local conservé, consulté en lecture seule le 24 septembre 2026 à 06:36:44 UTC. Les exports originaux restent hors Git ; aucune capture authentique de l'interface MLflow n'a été constituée.

| Fichier | Rôle |
| --- | --- |
| `summary.json` | Version, run, alias observé, paramètres et métriques enregistrés. |
| `dataset_info.json` | Résumé du corpus exporté sans chemin privé du snapshot. |
| `classification_report.json` | Rapport par classe exporté du run. |
| `confusion_matrix.json` | Matrice de confusion exportée du run. |
| `MANIFEST.json` | Provenance, empreintes des copies et des exports d'origine, transformations et manques. |

Les fichiers JSON ont été sélectionnés ou re-sérialisés pour ce dossier : **leurs SHA-256 sont ceux des copies assainies**, distincts des empreintes des exports privés et des artefacts du registre. Le hash du dataset est la valeur **enregistrée** par le run ; le contenu du snapshot n'a pas été réhaché indépendamment. Aucune donnée d'avis, capture d'interface ou binaire de modèle n'est inclus.

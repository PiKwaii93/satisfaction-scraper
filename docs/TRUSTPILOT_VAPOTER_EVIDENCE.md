# Preuve assainie — collecte Trustpilot Vapoter

La collecte privée concerne `www.vapoter.fr` sur Trustpilot. Les 16 vues linguistiques disponibles ont été parcourues jusqu'à leur fin naturelle. La réconciliation hors ligne des pages sauvegardées établit **11 281 identifiants Trustpilot uniques**, sans collision entre corpus. Il ne s'agit pas d'un instantané parfaitement simultané : les compteurs live ont évolué pendant la collecte.

| Élément contrôlé | Résultat |
| --- | ---: |
| Vues linguistiques et pages `completed` | 16 et 476 |
| Avis principaux et empilés | 9 261 et 2 020 |
| Identifiants uniques | 11 281 |
| Réponses d'entreprise présentes | 9 473 |
| Champs obligatoires valides | 11 281 / 11 281 |
| Doublons internes et collisions inter-corpus | 0 et 0 |
| Piles incomplètes et erreurs persistantes | 0 et 0 |

La note et l'indicateur de réponse ont été recalculés hors ligne depuis le corpus global privé vérifié par son SHA-256. Ce tableau représente la **distribution des notes dans le corpus collecté**, et non une répartition officielle affichée par Trustpilot à un instant donné.

| Note | Avis collectés | Avec réponse | Sans réponse | Taux de réponse |
| ---: | ---: | ---: | ---: | ---: |
| 1 étoile | 289 | 265 | 24 | 91,70 % |
| 2 étoiles | 115 | 95 | 20 | 82,61 % |
| 3 étoiles | 239 | 175 | 64 | 73,22 % |
| 4 étoiles | 1 030 | 786 | 244 | 76,31 % |
| 5 étoiles | 9 608 | 8 152 | 1 456 | 84,85 % |
| **Total** | **11 281** | **9 473** | **1 808** | **83,97 %** |

Pour l'indicateur académique, **« avis négatifs » signifie opérationnellement notes 1 et 2 étoiles** : 404 avis, dont 360 avec réponse et 44 sans réponse, soit **89,11 %** de réponses visibles. Le regroupement alternatif 1–3 étoiles compte 643 avis, dont 535 avec réponse et 108 sans réponse (83,20 %) ; il n'est pas désigné comme « négatif » par défaut. Cette convention est fondée sur la note Trustpilot, et non sur le sentiment prédit par le modèle.

Chaque vue a atteint `natural_end_reached` selon la pagination réelle. Chaque *review stack* a été développée et son nombre d'identifiants supplémentaires a été comparé au nombre annoncé. La sauvegarde a été atomique par page, avec empreinte SHA-256 ; les 476 empreintes de pages ont été vérifiées. L'union des identifiants stables a été contrôlée hors ligne. La période enregistrée va du 29 au 30 septembre 2026 (UTC).

Le collecteur publié est au commit `d19a0f9ebe6c1d4b07fdae9f86412f69890c1673`. La CI automatique `36713495695` a réussi pour backend, frontend et Docker ; le test E2E manuel était ignoré sur ce push. Cette CI valide le code, tandis que les manifestes privés et la réconciliation prouvent l'exécution de la collecte.

Empreintes des fichiers globaux privés, conservés hors Git :

| Fichier privé | SHA-256 |
| --- | --- |
| `reviews.jsonl` | `8da01889b3fb156af1ae138ce44b689c12b6226af39fe75c35f8c0adfaaa479e` |
| `manifest.json` | `e85fd46f8e79ef5753d280490605fc0c697e82f4d83b8298b648ac23a6b35be0` |

Le [résumé JSON public](../data/evidence/trustpilot_vapoter_collection_summary.json) ne contient que des agrégats. L'[exemple d'avis JSON](../data/evidence/trustpilot_review_example_synthetic.json) est fictif et explicitement marqué comme tel. Aucun texte d'avis, auteur, réponse, cookie, token ou chemin local privé n'est publié.

## Métadonnées du profil observées en direct

Observation ponctuelle le **30 septembre 2026 à 16:27, heure de Paris**, sur [le profil canonique Trustpilot](https://fr.trustpilot.com/review/www.vapoter.fr) : nom commercial **Vapoter**, **TrustScore 4,8 / 5** et **11 281 avis affichés**. La catégorie déclarée est **« Magasin de cigarettes électroniques »**, dans la hiérarchie **« Aliments, boissons & tabac » → « Tabac & cigarettes » → « Magasin de cigarettes électroniques »**. Le nom juridique complet n'est pas démontré.

| Note | Part affichée | Nombre donné par l'infobulle Trustpilot |
| ---: | ---: | ---: |
| 1 étoile | 3 % | 289 |
| 2 étoiles | 1 % | 115 |
| 3 étoiles | 2 % | 239 |
| 4 étoiles | 9 % | 1 030 |
| 5 étoiles | 85 % | 9 608 |
| **Total des comptes affichés** | **100 %** | **11 281** |

Ces valeurs sont des **métadonnées affichées par Trustpilot lors d'une observation ponctuelle**. Elles sont distinctes des données réconciliées du corpus privé. Les comptes par étoile observés en direct concordent numériquement avec ceux du corpus, sans prouver que les deux ensembles correspondent exactement au même instantané d'identifiants. Le compteur enregistré dans le manifeste français était auparavant de **11 282 le 29 septembre 2026 à 11:12 UTC**, puis de **11 281 le 30 septembre 2026 à 08:27 UTC** ; ces compteurs live ne servent pas de preuve de cardinalité du corpus.

**Portée de la preuve.** Les vues accessibles ont été parcourues jusqu'à leur fin naturelle pendant la période de collecte. Le total n'établit pas la couverture de tous les avis ayant jamais existé, ni une photographie instantanée unique. Les compteurs de l'interface ne prouvent pas la cardinalité du corpus. Les textes privés n'ont pas été importés dans l'application ni utilisés pour un nouvel entraînement. Le nom juridique complet reste inconnu ; la publication des verbatims exigerait une base de réutilisation documentée.

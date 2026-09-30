# Collecte des avis — protocole, résultat et limites de preuve

Source Markdown du PDF explicatif demandé par le sujet. Le résultat final concerne **www.vapoter.fr** sur Trustpilot. Les avis bruts et les réponses restent dans des corpus privés hors Git ; seuls les agrégats et empreintes sont publiés.

## Exigence et périmètre

Le sujet demande des métadonnées d'entreprises (domaine/thème, nombre d'avis, TrustScore, répartition des notes), puis les commentaires d'une entreprise comptant plus de 10 000 avis, leurs notes et l'information relative aux réponses aux avis négatifs. Il demande un PDF explicatif et un exemple JSON. La collecte technique et l'import dans l'application sont des étapes distinctes : le corpus Vapoter n'a pas été importé en base ni utilisé pour réentraîner le modèle.

## Historique, distinct de la preuve finale

| Élément | Portée réelle |
| --- | --- |
| [JSON historique Showroomprivé](../data/showroom_reviews.json) | 1 200 objets ; provenance, parcours de pages et droits de réutilisation insuffisamment documentés. Exemple technique historique, sans preuve de collecte exhaustive. |
| [Tentative Showroomprivé HTTP 403](../data/evidence/trustpilot_showroomprive_representative.json) | Zéro avis extrait. Trace d'une tentative bloquée, et non résultat final du projet. |

Le total d'avis affiché par Trustpilot lors de cette ancienne tentative ne représentait pas un nombre d'avis collectés. Les tests et la collecte finale n'ont pas contourné les protections de la plateforme. Le droit de réutilisation ou de publication des textes d'avis n'est pas établi par la seule accessibilité de la page : aucun verbatim n'est publié ici.

## Métadonnées de plateforme observées ponctuellement

Le **30 septembre 2026 à 16:27 (Europe/Paris)**, le [profil Trustpilot canonique de Vapoter](https://fr.trustpilot.com/review/www.vapoter.fr) affichait le nom commercial **Vapoter**, un **TrustScore de 4,8 / 5** et **11 281 avis**. La catégorie était **« Magasin de cigarettes électroniques »**, dans la hiérarchie **« Aliments, boissons & tabac » → « Tabac & cigarettes » → « Magasin de cigarettes électroniques »**. Le nom juridique complet n'a pas été démontré.

| Note | Pourcentage affiché | Compte affiché dans l'infobulle |
| ---: | ---: | ---: |
| 1 étoile | 3 % | 289 |
| 2 étoiles | 1 % | 115 |
| 3 étoiles | 2 % | 239 |
| 4 étoiles | 9 % | 1 030 |
| 5 étoiles | 85 % | 9 608 |

Ces valeurs sont des **métadonnées live affichées par Trustpilot lors d'une observation ponctuelle**. Elles sont distinctes des statistiques du corpus privé décrites ci-dessous. Les comptes par étoile concordent numériquement avec le corpus réconcilié, sans démontrer que les deux ensembles contiennent exactement les mêmes identifiants au même instant.

## Collecte finale Vapoter

Les **16 vues linguistiques disponibles** ont été parcourues séparément jusqu'à leur **fin naturelle constatée dans la pagination**. Chaque page a été vérifiée avant d'être marquée `completed` : statut et URL, filtre linguistique, expansion de toutes les *review stacks*, correspondance entre avis empilés attendus et identifiants révélés, champs obligatoires, puis écriture atomique et SHA-256. Les identifiants Trustpilot stables servent à la déduplication. Une réconciliation hors ligne a vérifié les pages et les collisions entre corpus.

| Contrôle | Résultat vérifié |
| --- | ---: |
| Vues linguistiques / pages `completed` | 16 / 476 |
| Avis principaux / empilés | 9 261 / 2 020 |
| Identifiants uniques après réconciliation | **11 281** |
| Réponses d'entreprise présentes | 9 473 |
| Avis avec champs obligatoires valides | 11 281 / 11 281 |
| Doublons internes / collisions inter-corpus | 0 / 0 |
| Piles incomplètes / pages en erreur persistante | 0 / 0 |

L'égalité **9 261 + 2 020 = 11 281** porte sur les enregistrements réconciliés. La période de sauvegarde enregistrée s'étend du 29 au 30 septembre 2026 (UTC). Le collecteur correspond au commit `d19a0f9ebe6c1d4b07fdae9f86412f69890c1673`, validé par la CI `36713495695` (backend, frontend et Docker réussis ; E2E manuel ignoré sur push).

La distribution suivante est **calculée sur les avis effectivement sauvegardés**, sans être présentée comme la distribution live de Trustpilot.

| Note | Avis | Avec réponse | Sans réponse | Taux de réponse |
| ---: | ---: | ---: | ---: | ---: |
| 1 étoile | 289 | 265 | 24 | 91,70 % |
| 2 étoiles | 115 | 95 | 20 | 82,61 % |
| 3 étoiles | 239 | 175 | 64 | 73,22 % |
| 4 étoiles | 1 030 | 786 | 244 | 76,31 % |
| 5 étoiles | 9 608 | 8 152 | 1 456 | 84,85 % |
| **Total** | **11 281** | **9 473** | **1 808** | **83,97 %** |

La définition opérationnelle principale des **avis négatifs** est : **notes 1 et 2 étoiles**. Le corpus en contient **404**, dont **360 avec réponse** et **44 sans réponse**, soit un taux de réponse visible de **89,11 %**. Le regroupement alternatif 1–3 étoiles donnerait 643 avis, 535 réponses et 108 sans réponse (83,20 %) ; il n'est pas qualifié automatiquement de négatif. Ces chiffres viennent des indicateurs de réponse enregistrés, sans publication des réponses ni des commentaires.

La [preuve publique assainie](TRUSTPILOT_VAPOTER_EVIDENCE.md) et le [résumé JSON agrégé](../data/evidence/trustpilot_vapoter_collection_summary.json) donnent la méthode et les contrôles sans révéler les avis. Le corpus global privé `reviews.jsonl` a pour SHA-256 `8da01889b3fb156af1ae138ce44b689c12b6226af39fe75c35f8c0adfaaa479e` ; son manifeste privé a pour SHA-256 `e85fd46f8e79ef5753d280490605fc0c697e82f4d83b8298b648ac23a6b35be0`. Ces empreintes identifient les fichiers vérifiés ; elles ne rendent pas leurs textes publics.

L'[exemple JSON synthétique](../data/evidence/trustpilot_review_example_synthetic.json), marqué `synthetic_example: true`, illustre les champs d'un avis, sa langue, sa provenance et une réponse éventuelle. Ce n'est **pas** un avis collecté. Le résumé agrégé et cet exemple ont des rôles distincts.

## Statut de l'exigence > 10 000 : DÉMONTRÉ POUR LE PARCOURS DES VUES ACCESSIBLES LORS DE LA COLLECTE

Les 16 vues linguistiques disponibles ont été parcourues jusqu'à leur fin naturelle. La réconciliation hors ligne des pages sauvegardées établit **11 281 identifiants Trustpilot uniques**, sans collision entre corpus. Cela démontre une collecte réelle de plus de 10 000 avis pour une entreprise ; ce n'est ni un instantané parfaitement simultané ni la preuve de tous les avis ayant jamais existé. Les compteurs live de l'interface ont évolué et ne servent pas de preuve de cardinalité. Les textes restent privés.

Les manifestes privés démontrent l'identifiant d'entreprise `www.vapoter.fr`, les URL des pages et des compteurs UI datés : 11 282 le 29 septembre 2026 à 11:12 UTC puis 11 281 le 30 septembre à 08:27 UTC. Le TrustScore, la catégorie et la répartition affichée ci-dessus proviennent d'une observation live ultérieure, distincte des manifestes. La distribution calculée sur les avis collectés ne doit pas être confondue avec cette observation, même si leurs comptes concordent numériquement. L'autorisation de réutilisation publique des avis bruts reste à documenter si une publication était envisagée.

## Présentation honnête au jury

« L'ancienne tentative Showroomprivé a reçu HTTP 403 et n'a extrait aucun avis ; le JSON historique de 1 200 avis ne prouve pas sa provenance. La preuve finale est la collecte privée Vapoter : 16 vues linguistiques parcourues jusqu'à leur fin naturelle, 476 pages sauvegardées et 11 281 identifiants uniques réconciliés, sans collision. Les avis bruts ne sont pas publiés. La collecte a duré plusieurs sessions, donc ce nombre n'est pas un instantané simultané ; nous montrons séparément les métadonnées de profil observées ponctuellement, les agrégats et empreintes du corpus, ainsi que les droits de republication et le nom juridique qui restent à établir. »

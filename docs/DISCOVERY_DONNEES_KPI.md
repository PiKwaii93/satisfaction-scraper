# Discovery — données, analyses et quatre KPI métier

Source de cadrage académique, établie le 22 septembre 2026. Elle complète l'Experience Map hypothétique de [cadrage_projet.md](../cadrage_projet.md). **Aucun entretien, questionnaire ni test utilisateur n'a été réalisé** : les besoins ci-dessous sont des hypothèses à confronter à des interlocuteurs réels, et non des résultats d'enquête.

## Interlocuteurs envisagés et questions de cadrage

| Partie prenante envisagée | Besoin à confirmer | Question à poser si un entretien devient possible |
| --- | --- | --- |
| Responsable service client | Repérer les avis négatifs et savoir si une réponse visible existe. | Comment les avis à traiter sont-ils aujourd'hui priorisés ? |
| Responsable supply chain | Repérer les irritants de livraison, sans déduire une cause logistique d'un simple mot-clé. | Quels incidents opérationnels peuvent être reliés à des avis ? |
| Responsable expérience client | Suivre note et sentiment sur une période et une source connues. | Quelle variation justifie une investigation ? |
| Analyste data | Vérifier provenance, doublons, dates, couverture et version du modèle. | Quelles sources et autorisations de réutilisation sont disponibles ? |
| Direction | Arbitrer sur des indicateurs contextualisés et leurs limites. | Quel indicateur déclencherait une décision concrète ? |

Ces personnes sont des **profils envisagés**, pas des personnes contactées. La carte de parcours décrit le point de vue supposé du responsable service client et doit être lue comme une hypothèse de travail.

## Données nécessaires et état disponible

| Donnée | Usage dans l'analyse | Disponibilité / limite actuelle |
| --- | --- | --- |
| Entreprise, domaine, source, identifiant du run, mode et raison d'arrêt de collecte | Définir le périmètre de chaque résultat. | Métadonnées et provenance partiellement présentes ; le domaine peut être renseigné par l'utilisateur et n'est pas nécessairement inféré de la source. |
| Nombre total d'avis annoncé par la source, TrustScore et distribution des étoiles | Comparer le corpus traité au contexte de la source. | Présents dans certaines métadonnées ; le total affiché n'est jamais le nombre collecté. |
| Identifiant d'avis, verbatim, note, date, réponse de l'entreprise | Dédupliquer, calculer note et réponse, filtrer par période. | Données variables selon la source ; un champ absent ne signifie pas « aucune réponse ». |
| Sentiment, score, version du modèle et thèmes détectés | Mesurer le sentiment et explorer les irritants. | Prédictions historisées et thèmes lexicaux disponibles ; les prédictions et mots-clés peuvent se tromper. |

Pour évaluer l'existant, on vérifie d'abord la provenance et l'autorisation d'usage, le nombre de lignes réellement extraites, les doublons, champs manquants, dates exploitables et la part du corpus couverte. On compare ensuite notes et sentiments, puis on lit des exemples d'avis pour contrôler les désaccords et les thèmes. Les analyses par entreprise, source et période ne sont comparables que si leur périmètre et leur mode de collecte le permettent. L'artefact [Showroomprivé](../data/evidence/trustpilot_showroomprive_representative.json) indique HTTP 403 et zéro avis extrait : aucun KPI client ne peut en être calculé.

## Les quatre KPI retenus

Période commune : intervalle des dates d'avis **effectivement exploitables** du run, affiché avec la date du run. Si les dates d'avis manquent, afficher « période des avis inconnue » et ne pas inventer un suivi temporel. Calcul par entreprise et source ; afficher le nombre d'avis du corpus et le mode de collecte. Un run filtré par étoiles, limité par l'utilisateur ou interrompu n'est pas représentatif de tous les clients. Le drapeau de représentativité du code n'est positif que pour une collecte `representative` ayant effectivement abouti selon ses critères : [analysis_service.py](../app/api/services/analysis_service.py).

| KPI | Définition / formule | Données et calcul actuels | Décision possible et garde-fou |
| --- | --- | --- | --- |
| **Note moyenne** | Somme des notes valides / nombre de notes valides. | `AVG(r.rating)` dans la synthèse du run. | Repérer une évolution de satisfaction déclarée ; indiquer effectif, période, source et biais de collecte. |
| **Part d'avis à sentiment négatif** | Nombre d'avis prédits `Négatif` / nombre d'avis avec prédiction exploitable × 100. | Distribution des prédictions et `negative_rate` dans la synthèse. | Prioriser la lecture des verbatims ; nommer la version du modèle et sa marge d'erreur, notamment pour `Neutre`. |
| **Taux de réponse visible de l'entreprise** | Nombre d'avis avec réponse visible / nombre d'avis dont le statut de réponse est **connu** × 100. | `responded_count` et `review_count` existent, mais la base stocke un booléen : une valeur absente importée peut être assimilée à `false`. | Mesurer la réponse publique **seulement** pour une source dont le champ réponse est systématiquement renseigné. Sinon afficher « non calculable » ; ne pas prendre le ratio brut pour une preuve. Ce KPI porte sur tous les avis, pas seulement les négatifs. |
| **Volume d'avis analysés — couverture du corpus** | Nombre d'avis distincts effectivement analysés dans le run. Si un total source fiable est disponible : couverture indicative = avis analysés / total source × 100. | `review_count`, `unique_reviews`, total annoncé par la source lorsque disponible. | Qualifier la solidité et le périmètre des trois autres KPI ; **ce n'est pas une mesure directe de satisfaction**. Ne pas assimiler volume affiché et volume extrait. |

Le code détecte le thème `livraison`, mais le rapport présente seulement les quatre premières priorités par nombre d'avis négatifs. L'absence de `livraison` de cette liste ne donne donc pas un taux exhaustif. La liste `critical_reviews` est elle aussi plafonnée à dix exemples. Ni « part livraison » ni « part d'avis critiques » ne remplace honnêtement le quatrième KPI sans calcul supplémentaire ; aucun code n'est ajouté pour ce chantier documentaire.

## Timeline de cadrage et ressources

| Période attestée ou conditionnelle | Livrable / décision | Ressources |
| --- | --- | --- |
| État documenté au 22/09/2026 | Personas hypothétiques, Experience Map, inventaire des données et preuves existantes. | Équipe projet ; dépôt Git, code, PostgreSQL, MLflow et runs GitHub existants. |
| Prochaine revue documentaire, avant soutenance (date non communiquée) | Valider quatre définitions, sources, dénominateurs et limites ; relire avec le PDF normatif. | Équipe projet et relecture métier si disponible ; aucun achat prévu. |
| Si accès à des interlocuteurs ou données autorisées | Confirmer/infirmer les hypothèses et réviser la carte ; étape non réalisée à ce jour. | Temps des interlocuteurs et droit d'accès à convenir ; coût non chiffré. |

Les outils logiciels libres et la VM scolaire existent déjà. Leur **coût marginal pour cette rédaction** n'implique pas un coût économique nul : temps humain, hébergement alloué et éventuelles licences bureautiques restent à chiffrer si le jury demande un budget complet.

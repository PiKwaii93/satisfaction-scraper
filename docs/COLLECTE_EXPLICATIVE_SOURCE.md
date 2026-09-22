# Collecte des avis — protocole, JSON et limites de preuve

Source Markdown à valider avant le **PDF explicatif** demandé par le sujet. État au 22 septembre 2026. Cette note décrit les données réellement disponibles ; elle ne certifie pas une collecte exhaustive.

## Exigence et champs attendus

Le sujet demande les informations générales d'entreprises (dont domaine/thème), le nombre d'avis, TrustScore et répartition des notes, puis tous les commentaires d'une entreprise comptant plus de 10 000 avis, avec notes et information sur les réponses aux avis négatifs. Il demande un fichier explicatif DOC/PDF et un exemple JSON. Les champs du JSON doivent distinguer les **métadonnées affichées par la source**, les **avis réellement extraits** et les **résultats d'analyse**.

## Provenance et traitement actuel

Le code propose deux modes de collecte : `sampled` pour un échantillon équilibré par étoiles et `representative` suivant l'ordre naturel. Il enregistre pages traitées, volume unique, erreurs et raison d'arrêt. Le service d'analyse refuse de qualifier de représentatifs les KPI d'un échantillon filtré ou d'une collecte représentative incomplète : [analysis_service.py](../app/api/services/analysis_service.py). Le domaine d'entreprise peut être fourni par l'utilisateur ; il ne doit pas être annoncé comme une catégorie automatiquement déduite du site. Un import CSV/JSON constitue une autre provenance et nécessite de connaître l'autorisation associée au fichier.

Le JSON [trustpilot_showroomprive_representative.json](../data/evidence/trustpilot_showroomprive_representative.json) est un **exemple de structure et de trace d'échec**, pas un échantillon d'avis collectés : métadonnées affichant `total_reviews=264792` et `trustscore=3.9`, mais `reviews_extracted=0`, `unique_reviews=0`, `stop_reason=platform_limitation` et `error=http_403`. Le tableau `reviews` est vide. Ces valeurs ne prouvent ni 10 000 avis extraits ni leur répartition réelle dans un corpus. Le fichier historique [showroom_reviews.json](../data/showroom_reviews.json) contient un lot antérieur limité ; il ne prouve pas la collecte exhaustive demandée.

## Statut de l'exigence > 10 000 : NON CONFORME

Aucune preuve actuelle ne montre la récupération directe de tous les commentaires d'une entreprise comptant plus de 10 000 avis. Ne pas relancer Trustpilot pour contourner HTTP 403, modifier les protections ou présenter les métadonnées de la page comme des avis capturés.

Trois pistes admissibles à **étudier**, sans les déclarer conformes avant validation :

1. **API officielle**, par exemple [Google Business Profile `reviews.list`](https://developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list), avec accès accordé au compte propriétaire et établissement vérifié. Vérifier volume réellement disponible, pagination, droits d'export et correspondance avec « commentaires d'une entreprise » du sujet.
2. **Export autorisé par l'entreprise** ou par la plateforme, accompagné de la permission, du périmètre, du nombre d'avis et de la méthode d'obtention. Un export n'est pas automatiquement une collecte web directe ; préciser ce point au jury.
3. **Jeu public sous licence adaptée**, avec URL, licence, date, identifiant d'entreprise et couverture prouvée. Vérifier si le mode de collecte déjà effectué par un tiers est accepté par le sujet. Une simple présence en ligne n'établit pas le droit de réutilisation.

Pour chaque éventuelle piste, archiver : permission/licence et date, source, entreprise, total annoncé, nombre de lignes réellement disponibles, doublons, période, notes, réponses, format JSON d'exemple et raison de tout écart. Les recommandations [CNIL sur la réutilisation de données en ligne](https://www.cnil.fr/fr/recommandations-reutilisateurs-donnees-internet) et les [conditions Trustpilot](https://uk.corporate.trustpilot.com/legal/for-businesses/terms-of-use-and-sale-for-businesses/nov-2025) sont des points de contrôle, pas des autorisations implicites.

## Présentation honnête au jury

« Le pipeline de collecte et les métadonnées sont implémentés, mais notre tentative documentée sur l'entreprise cible a reçu HTTP 403 avant l'extraction du premier avis. Nous n'avons donc pas démontré la collecte exhaustive de plus de 10 000 avis. Nous avons conservé l'erreur, distingué le total affiché du nombre extrait et limité les KPI au corpus réellement analysé. Une source sous autorisation explicite serait nécessaire pour fermer cet écart. »

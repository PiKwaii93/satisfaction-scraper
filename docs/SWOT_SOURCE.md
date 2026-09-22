# SWOT — contenu source de l'unique slide PowerPoint

Texte à valider avant toute génération du `.pptx`. Format cible du sujet : **une slide, quatre quadrants, bullet points**. État du projet au 22 septembre 2026.

## Forces

- Chaîne démontrée de l'import à l'analyse et au tableau de bord ; authentification JWT et rôles présents.
- Évaluation ML dédupliquée ; modèle v53 documenté et identifiable dans le registre MLflow conservé.

## Faiblesses

- Collecte directe de tous les avis d'une entreprise comptant plus de 10 000 avis **non démontrée** : tentative Trustpilot bloquée par HTTP 403.
- Corpus et classe `Neutre` limités ; accessibilité et conformité RGPD non auditées de bout en bout.

## Opportunités

- Obtenir des données fournies avec autorisation par une entreprise pour confirmer les irritants et guider les corrections.
- Analyser les retours sur la livraison pour envisager moins de reprises de transport ou de traitements inutiles : **bénéfice RSE hypothétique, non mesuré**.

## Menaces

- Restrictions d'accès des plateformes et évolution des règles de réutilisation ; verbatims pouvant contenir des données personnelles.
- Échantillons biaisés ou prédictions imparfaites pouvant orienter les décisions à tort ; ressources limitées de la VM scolaire.

La SWOT ne prétend pas démontrer un gain environnemental ou une conformité légale. Les limites de collecte et de représentativité doivent rester visibles sur la slide. La checklist MLflow existe, mais le dossier final de captures/export de v53 reste à constituer.

# Product Roadmap — Satisfaction Client

## Objet du document

Ce fichier décrit la trajectoire produit actuelle de Satisfaction Client.

Le code, les tests et Git restent les sources de vérité. Les statuts indiqués ici doivent être vérifiés dans le dépôt avant toute nouvelle implémentation.

## Vision produit

Transformer Satisfaction Client en un SaaS B2B multi-clients permettant à chaque organisation de :

* importer ou collecter ses avis clients ;
* analyser la satisfaction et les irritants ;
* comparer les résultats dans le temps ;
* gérer des alertes métier ;
* corriger les prédictions ;
* améliorer progressivement la qualité du modèle ;
* accéder uniquement à ses propres données.

## Légende des statuts

* **Terminé et vérifié pour le périmètre actuel** : présent dans le code et validé au moins partiellement par les tests ou contrôles existants.
* **Partiellement implémenté** : une base existe, mais le chantier n’est pas complet.
* **Non commencé** : aucune implémentation significative confirmée.
* **À revisiter** : choix actuellement utilisé, mais insuffisant pour un vrai déploiement SaaS.

---

# État actuel des jalons

## Jalon 1 — Identité et espaces client

**Statut : Terminé et vérifié pour le périmètre du MVP local**

### Présent

* organisations ;
* utilisateurs ;
* authentification email/mot de passe ;
* JWT Bearer ;
* rôles `admin` et `member` ;
* invitations ;
* compte administrateur de démonstration ;
* isolation des données par organisation ;
* écran de connexion ;
* chargement de la session utilisateur ;
* affichage de l’organisation active ;
* déconnexion ;
* restrictions sur les actions sensibles.

### À améliorer ultérieurement

* stockage du token plus robuste que `localStorage` ;
* rotation ou révocation des tokens ;
* récupération de mot de passe ;
* MFA ;
* SSO ;
* gestion avancée des sessions ;
* tests frontend automatisés de l’authentification.

### Critère de sortie SaaS

Le jalon sera réellement prêt pour la production lorsque l’authentification aura été durcie, auditée et testée sur le frontend et le backend.

---

## Jalon 2 — Sources d’avis professionnelles

**Statut : Partiellement implémenté**

### Présent

* Trustpilot comme source web active ;
* import CSV ;
* détection et mapping des colonnes ;
* sources configurables par organisation ;
* abstraction préparant plusieurs types de sources.

### Sources préparées mais non réellement connectées

* Google Reviews ;
* Zendesk ;
* Shopify ;
* support ou SAV interne.

### Travail restant

* documenter précisément les formats CSV supportés ;
* améliorer les messages d’erreur et la validation des imports ;
* choisir le premier véritable connecteur professionnel ;
* gérer les secrets et autorisations des connecteurs ;
* prévoir la synchronisation et la reprise sur erreur ;
* tracer les imports et synchronisations.

### Critère de sortie

Au moins un connecteur professionnel doit fonctionner de bout en bout, avec authentification, synchronisation, erreurs, journalisation et tests.

---

## Jalon 3 — Valeur métier client

**Statut : Largement implémenté**

### Présent

* rapports d’analyse ;
* KPIs ;
* avis critiques ;
* irritants ;
* tendances entre runs ;
* benchmark ;
* alertes métier ;
* centre d’action client ;
* historique et journal d’activité ;
* exports CSV ;
* rapport imprimable côté navigateur.

### Travail restant

* confirmer la pertinence métier des alertes avec de vrais utilisateurs ;
* améliorer la priorisation des actions ;
* permettre davantage de comparaisons par période ;
* affiner l’évolution des irritants ;
* mesurer l’usage réel des fonctionnalités ;
* ajouter des notifications ou mécanismes d’escalade si nécessaire.

### Critère de sortie

Les indicateurs et alertes doivent permettre à un utilisateur métier de décider clairement quoi traiter en priorité.

---

## Jalon 4 — Qualité IA et gouvernance

**Statut : Partiellement implémenté**

### Présent

* corrections humaines ;
* réentraînement ;
* historique des entraînements ;
* versionnement avec MLflow ;
* suivi de la version de production ;
* pondération des corrections humaines.

### Travail restant

* clarifier la stratégie entre modèle global et modèles par organisation ;
* définir les droits d’un administrateur produit global ;
* mesurer les performances par version ;
* mettre en place un suivi de dérive ;
* définir des seuils de confiance ;
* empêcher un réentraînement inadapté avec trop peu de données ;
* formaliser les règles de promotion d’un modèle en production ;
* définir la gouvernance des données utilisées pour l’entraînement.

### Critère de sortie

Chaque version du modèle doit être mesurée, traçable, comparable et promue selon des règles explicites.

---

## Jalon 5 — Industrialisation

**Statut : Partiellement commencé**

### Présent

* Docker Compose ;
* CI GitHub Actions ;
* tests backend ;
* fondation de tests frontend avec Vitest, React Testing Library et MSW ;
* build frontend automatisable ;
* PostgreSQL ;
* Redis et Celery ;
* MLflow.

### Travail restant prioritaire

* étendre les tests frontend aux imports CSV, alertes et corrections ;
* lint frontend ;
* découpage progressif du frontend monolithique ;
* migrations de base de données versionnées ;
* gestion sécurisée des secrets ;
* durcissement de l’authentification ;
* monitoring applicatif ;
* logs structurés ;
* sauvegardes PostgreSQL ;
* déploiement cloud ;
* politique RGPD ;
* rétention et suppression des données ;
* gestion des incidents ;
* stratégie de restauration.

### Critère de sortie

Le produit doit être déployable, observable, sauvegardé, sécurisé et maintenable sans dépendre uniquement de l’environnement local.

---

# Priorités recommandées

## Priorité 1 — Fondation de tests frontend

**Statut : Terminée pour le périmètre initial**

### Valeur

Réduire le risque de régression sur les parcours de connexion, permissions, imports, alertes et corrections.

### Périmètre initial

* installer une infrastructure de tests cohérente avec React et Vite ;
* tester l’écran de connexion ;
* tester une session authentifiée ;
* tester les différences entre `admin` et `member` ;
* tester une erreur API `401` ;
* tester au moins un parcours métier critique ;
* ajouter la commande de test à la CI.

### Réalisé

* Vitest et jsdom configurés avec Vite ;
* React Testing Library et user-event installés ;
* MSW configuré pour les scénarios HTTP ;
* écran de connexion testé ;
* connexion et restauration de session testées ;
* restrictions `admin` / `member` testées ;
* expiration `401` testée ;
* lancement Trustpilot testé ;
* tests frontend exécutés dans la CI.

### Risque

Moyen, principalement en raison du caractère monolithique de `App.tsx`.

---

## Priorité 2 — Migrations de base de données versionnées

**Statut : Terminée pour le périmètre actuel**

### Valeur

Sécuriser les évolutions de schéma et préparer un déploiement réel.

### Périmètre

* auditer le schéma idempotent actuel ;
* choisir un outil de migration ;
* créer une base de migration à partir du schéma existant ;
* préserver les données locales ;
* documenter les procédures de migration et de rollback.

### Réalisé

* Alembic retenu et intégré au runtime FastAPI/Celery ;
* baseline initiale du schéma produit ;
* validation avant adoption des bases existantes non versionnées ;
* verrou PostgreSQL contre les migrations concurrentes ;
* CLI explicite pour `upgrade`, `current` et `downgrade` ;
* tests PostgreSQL sur base neuve, données existantes et schéma partiel ;
* PostgreSQL de test ajouté à la CI ;
* tables historiques laissées hors du périmètre Alembic.

### Risque

Élevé, car le projet contient déjà des données et un mécanisme de migration au démarrage.

---

## Priorité 3 — Durcissement de l’authentification et des secrets

### Valeur

Réduire les risques de sécurité avant toute mise en ligne.

### Périmètre

* revoir le stockage du JWT ;
* séparer les secrets de développement et de production ;
* prévoir expiration, révocation et récupération de compte ;
* revoir les valeurs de démonstration ;
* ajouter des tests de sécurité et de permissions.

### Risque

Moyen à élevé.

---

## Priorité 4 — Premier connecteur professionnel réel

### Valeur

Rendre le produit utilisable avec une source d’avis métier autre que Trustpilot ou un CSV manuel.

### Périmètre

À choisir entre Google Business Profile, Zendesk ou une autre source après étude des besoins clients et des contraintes API.

### Risque

Variable selon l’API, l’authentification et les conditions d’accès.

---

## Priorité 5 — Monitoring, sauvegardes et déploiement

### Valeur

Préparer un environnement de démonstration ou de production fiable.

### Périmètre

* déploiement ;
* métriques ;
* journalisation ;
* alertes techniques ;
* sauvegardes ;
* restauration ;
* documentation d’exploitation.

### Risque

Élevé en raison du nombre de composants : frontend, API, PostgreSQL, Redis, Celery et MLflow.

---

# Prochain chantier recommandé

Le prochain chantier recommandé est :

> Durcir l'authentification et la gestion des secrets avant toute mise en ligne.

Le chantier migrations est terminé pour le périmètre actuel. Le prochain audit doit couvrir :

* le stockage et la révocation des JWT ;
* la séparation des secrets de développement et de production ;
* la récupération de compte ;
* les valeurs de démonstration ;
* les tests de sécurité et de permissions.

---

# Roadmap historique

La section suivante conserve le plan initial ayant guidé le passage du scraper à un SaaS B2B.

Elle est conservée pour référence, mais ne doit pas être utilisée directement comme plan d’exécution actuel.

## Plan initial

1. Identité et espaces client.
2. Sources d’avis professionnelles.
3. Valeur métier client.
4. Qualité IA et gouvernance.
5. Industrialisation.

Le jalon initial « Auth + Organisations » a depuis été implémenté pour le MVP local.

---

# Règles de maintenance

* Mettre à jour ce fichier lorsqu’un jalon ou une priorité change.
* Ne pas y documenter chaque petite modification technique.
* Mettre les tâches opérationnelles dans `CURRENT_TASK.md`.
* Mettre les décisions durables dans `ARCHITECTURE_DECISIONS.md`.
* Mettre les instructions d’installation et d’utilisation dans `README.md`.
* Vérifier chaque statut dans le code et dans les tests.
* Ne jamais présenter une source préparée comme un connecteur fonctionnel.

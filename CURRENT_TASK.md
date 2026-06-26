# Current Task

## Statut actuel

Aucune fonctionnalite produit n'est actuellement en cours d'implementation.

La documentation de transmission a ete creee puis fusionnee dans `main`.

Une roadmap produit actualisee est en cours d'ajout dans :

```text
PRODUCT_ROADMAP.md
```

Cette modification est exclusivement documentaire.

## Derniere tache terminee

Creation et validation de la documentation de passation initiale :

- `README.md`
- `AGENT_CONTEXT.md`
- `ARCHITECTURE_DECISIONS.md`
- `CURRENT_TASK.md`

Validations executees lors de cette tache :

- build frontend : OK ;
- tests backend : `50 passed`, `1 warning` ;
- `git diff --check` : OK.

La pull request correspondante a ete fusionnee dans `main`.

## Tache documentaire actuelle

Ajouter et integrer `PRODUCT_ROADMAP.md` afin de distinguer clairement :

- la vision produit ;
- les jalons deja termines ;
- les chantiers partiellement implementes ;
- les priorites recommandees ;
- le prochain chantier a proposer.

Fichiers concernes :

- `PRODUCT_ROADMAP.md`
- `README.md`
- `AGENT_CONTEXT.md`
- `CURRENT_TASK.md`

Aucun code applicatif ne doit etre modifie dans cette tache.

## Prochain chantier recommande

Apres fusion de la roadmap documentaire, le prochain chantier recommande est :

> Mettre en place une fondation de tests frontend automatises.

Le perimetre exact doit etre valide par l'utilisateur avant toute implementation.

Premiers parcours envisages :

- affichage de l'ecran de connexion ;
- comportement d'une session utilisateur authentifiee ;
- differences entre les roles `admin` et `member` ;
- gestion d'une erreur API `401` ;
- au moins un parcours metier critique deja present.

## Avant de commencer le prochain chantier

Le prochain agent doit :

1. lire `README.md` ;
2. lire `AGENT_CONTEXT.md` ;
3. lire `PRODUCT_ROADMAP.md` ;
4. lire `ARCHITECTURE_DECISIONS.md` ;
5. lire `CURRENT_TASK.md` ;
6. verifier `git status`, `git diff` et les derniers commits ;
7. inspecter le frontend reel ;
8. presenter sa comprehension, son plan, les risques et les criteres d'acceptation avant de modifier le code.

## Contraintes

- Ne pas lancer de refactoring general de `frontend/src/App.tsx` sans demande explicite.
- Ne pas commencer l'implementation des tests frontend sans validation du perimetre.
- Ne pas commit ou push sans autorisation.
- Ne pas presenter une source preparee comme un connecteur fonctionnel.
- Respecter l'isolation par `organization_id` et les roles `admin` / `member`.
- Le code, Git et les tests restent les sources de verite.

## Validations attendues pour la tache documentaire actuelle

```powershell
git diff --check
```

Aucun build applicatif ni test backend n'est obligatoire si seuls les fichiers Markdown sont modifies.

## Etat Git attendu

Avant commit :

- uniquement des modifications documentaires ;
- aucun fichier applicatif modifie ;
- aucun secret ajoute.

Apres fusion de la pull request :

- branche `main` a jour ;
- working tree propre.

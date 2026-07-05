# Current Task

## Statut actuel

La fondation de tests frontend automatises est en cours de finalisation sur la
branche :

```text
codex/frontend-test-foundation
```

Le comportement produit n'a pas ete refactore. Le chantier ajoute uniquement
l'infrastructure et les premiers scenarios de non-regression.

## Perimetre implemente

- Vitest avec environnement jsdom ;
- React Testing Library et user-event ;
- MSW pour les scenarios HTTP ;
- affichage de l'ecran de connexion ;
- connexion reussie ;
- restauration d'une session existante ;
- restrictions du role `member` ;
- lancement Trustpilot par un `admin` ;
- suppression du JWT local apres une erreur API `401` ;
- execution des tests frontend dans GitHub Actions.

## Fichiers principaux

- `frontend/src/App.test.tsx`
- `frontend/src/api.test.ts`
- `frontend/src/test/setup.ts`
- `frontend/src/test/server.ts`
- `frontend/vite.config.ts`
- `frontend/package.json`
- `.github/workflows/ci.yml`

## Validations attendues

```powershell
npm --prefix frontend test
npm --prefix frontend run build
docker-compose run --rm api sh -c "python -m pip install --disable-pip-version-check -q --timeout 120 --retries 5 -r requirements-dev.txt && python -m compileall app/api && pytest -q"
git diff --check
```

## Securite des dependances frontend

La vulnerabilite critique detectee sur `vitest@3.2.4` a ete corrigee en passant
a `vitest@3.2.6`. `npm audit` ne signale plus aucune vulnerabilite.

## Prochain chantier recommande

Apres fusion de cette branche :

> Introduire des migrations de base de donnees versionnees en preservant les
> donnees PostgreSQL locales existantes.

Ce chantier doit commencer par un audit de `init_db.sql` et
`app/api/database.py`. Aucun remplacement du mecanisme idempotent ne doit etre
fait sans strategie de baseline, migration et rollback.

## Contraintes durables

- Ne pas refactorer globalement `frontend/src/App.tsx` sans demande explicite.
- Respecter l'isolation par `organization_id` et les roles `admin` / `member`.
- Ne pas presenter une source preparee comme un connecteur fonctionnel.
- Ne pas committer `app/models/sentiment_model.pkl` apres un entrainement local
  sauf demande explicite.
- Ne pas commit ou push sans autorisation utilisateur.

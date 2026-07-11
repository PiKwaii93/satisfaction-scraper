# Current Task

## Statut actuel

Les migrations de base de donnees versionnees sont en cours de finalisation sur
la branche :

```text
codex/versioned-db-migrations
```

Le chantier remplace l'evolution SQL idempotente du schema produit par Alembic,
avec une strategie de baseline qui preserve les bases locales existantes.

## Perimetre implemente

- Alembic et une premiere revision du schema produit ;
- application automatique des revisions au demarrage ;
- verrou de migration PostgreSQL ;
- validation avant baseline d'une base existante ;
- refus des schemas partiels ;
- CLI `upgrade`, `current` et `downgrade` ;
- separation entre tables historiques et tables produit ;
- tests PostgreSQL temporaires ;
- service PostgreSQL dans la CI backend.

## Fichiers principaux

- `alembic.ini`
- `migrations/env.py`
- `migrations/versions/20260705_0001_product_schema_baseline.py`
- `app/api/database.py`
- `app/api/schema_migrations.py`
- `tests/test_database_migrations.py`
- `.github/workflows/ci.yml`

## Validations attendues

```powershell
npm --prefix frontend test
npm --prefix frontend run build
docker-compose run --rm api sh -c "python -m pip install --disable-pip-version-check -q --timeout 120 --retries 5 -r requirements-dev.txt && python -m compileall app/api migrations && pytest -q"
git diff --check
```

## Prochain chantier recommande

Apres fusion de cette branche :

> Durcir l'authentification et la gestion des secrets avant toute mise en ligne.

## Contraintes durables

- Ne pas refactorer globalement `frontend/src/App.tsx` sans demande explicite.
- Respecter l'isolation par `organization_id` et les roles `admin` / `member`.
- Ne pas presenter une source preparee comme un connecteur fonctionnel.
- Ne pas committer `app/models/sentiment_model.pkl` apres un entrainement local
  sauf demande explicite.
- Ne pas commit ou push sans autorisation utilisateur.

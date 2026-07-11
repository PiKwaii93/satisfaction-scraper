# Migrations produit

Alembic versionne uniquement les tables de l'application produit. Les tables
historiques `dim_companies` et `fact_reviews` restent gerees par `init_db.sql`.

Utiliser le module applicatif pour appliquer ou inspecter les migrations afin de
beneficier de la baseline securisee des bases locales existantes :

```powershell
docker-compose run --rm api python -m app.api.schema_migrations upgrade
docker-compose run --rm api python -m app.api.schema_migrations current
```

Un downgrade est destructif. Il exige une confirmation explicite :

```powershell
docker-compose run --rm api python -m app.api.schema_migrations downgrade --revision -1 --yes
```

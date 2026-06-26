# Current Task - Handoff documentation

## Objectif de cette tache

Creer une documentation de passation robuste pour de futurs agents IA qui travailleront sur ce projet avec Cursor, Claude Code, Gemini CLI ou Codex.

Cette tache ne doit pas ajouter de fonctionnalite produit.

## Demande utilisateur

L'utilisateur souhaite :

- un audit de l'etat reel du repo ;
- une documentation racine maintenable ;
- une clarification de l'architecture actuelle ;
- une separation entre faits verifies, incertitudes et prochaines priorites ;
- aucun secret copie en clair ;
- aucune commande inventee ;
- aucun commit ou push sans autorisation.

## Fichiers concernes

Fichiers crees ou mis a jour par cette tache :

- `README.md`
- `AGENT_CONTEXT.md`
- `CURRENT_TASK.md`
- `ARCHITECTURE_DECISIONS.md`

## Etat initial verifie

Commandes executees avant modification documentaire :

```powershell
git -c safe.directory=C:/Users/Maxen/OneDrive/Documents/GitHub/satisfaction-scraper status --short --branch
```

Resultat utile :

```text
## codex/platform-organizations
```

Le working tree etait propre. Git a affiche un avertissement local sur l'acces a un fichier de configuration utilisateur Git, sans impact constate sur le repo.

```powershell
git -c safe.directory=C:/Users/Maxen/OneDrive/Documents/GitHub/satisfaction-scraper diff --stat
git -c safe.directory=C:/Users/Maxen/OneDrive/Documents/GitHub/satisfaction-scraper diff --name-status
```

Resultat utile :

```text
Aucun diff.
```

```powershell
git -c safe.directory=C:/Users/Maxen/OneDrive/Documents/GitHub/satisfaction-scraper log --oneline --decorate -20
```

Dernier commit confirme :

```text
6d658f7 (HEAD -> codex/platform-organizations, origin/main, origin/HEAD, main) Merge pull request #35 from PiKwaii93/codex/actionable-home
```

## Etat produit confirme par inspection

### Existant

- Application React/Vite/TypeScript.
- API FastAPI.
- Auth JWT.
- Organisations et utilisateurs.
- Roles `admin` et `member`.
- Sources d'avis par organisation.
- Trustpilot et CSV actifs.
- Sources preparees Google Reviews, Zendesk, Shopify, support interne.
- Runs asynchrones via Celery + Redis.
- PostgreSQL.
- MLflow.
- Rapports entreprise.
- Tendances.
- Benchmark.
- Corrections humaines.
- Reentrainement modele.
- Alertes metier.
- Centre d'action client.
- Administration organisation.
- Tests backend.
- CI GitHub Actions.

### Historique encore present

- Dashboard Streamlit.
- Scripts `worker`.
- Tables `dim_companies` et `fact_reviews`.
- Exports JSON/CSV.
- Fichiers d'annotations.

Ces elements sont historiques mais encore dans le repo.

## Non confirme ou non implemente

Ne pas presenter ces points comme termines :

- vrais connecteurs Google Reviews, Zendesk, Shopify ou support interne ;
- paiement ou abonnement SaaS ;
- gestion multi-organisation globale par super-admin produit ;
- deploiement cloud ;
- monitoring de production complet ;
- backups PostgreSQL automatises ;
- politique RGPD/retention finalisee ;
- frontend tests automatises ;
- lint frontend ;
- migrations Alembic ;
- auth production hardening.

## Contradictions ou evolutions importantes

- Le projet s'appelle encore parfois Satisfaction Scraper dans l'historique, mais le produit actuel est Satisfaction Client.
- L'ancien dashboard principal etait Streamlit ; le frontend produit actuel est React.
- L'API key frontend a ete remplacee par JWT. Le fichier `app/api/security.py` existe encore mais n'est plus le chemin produit principal.
- Les sources "connecteurs" existent comme configuration produit, pas comme integrations completes.
- Le repo contient des valeurs locales de developpement pour certains secrets. Elles ne doivent pas etre recopiees dans la documentation publique.

## Validation a effectuer apres modification

Minimum demande :

```powershell
git diff --check
```

Validation raisonnable :

```powershell
npm --prefix frontend run build
```

```powershell
docker-compose run --rm api sh -c "python -m pip install --disable-pip-version-check -q --timeout 120 --retries 5 -r requirements-dev.txt && python -m compileall app/api && pytest -q"
```

## Resultats de validation

Validations executees pendant cette tache :

```powershell
npm --prefix frontend run build
```

Resultat :

```text
OK - Vite build termine.
```

```powershell
docker-compose run --rm api sh -c "python -m pip install --disable-pip-version-check -q --timeout 120 --retries 5 -r requirements-dev.txt && python -m compileall app/api && pytest -q"
```

Resultat :

```text
OK - 50 passed, 1 warning.
```

Warning observe :

```text
StarletteDeprecationWarning lie a FastAPI TestClient/httpx.
```

```powershell
git -c safe.directory=C:/Users/Maxen/OneDrive/Documents/GitHub/satisfaction-scraper diff --check
```

Resultat :

```text
OK - aucun probleme de whitespace signale.
```

Git affiche des avertissements locaux LF/CRLF et un avertissement d'acces au fichier Git utilisateur `C:\Users\Maxen/.config/git/ignore`. Aucun de ces avertissements n'a bloque les validations.

## Priorites pour le prochain agent

1. Verifier l'etat Git avant d'editer.
2. Lire `AGENT_CONTEXT.md` et `ARCHITECTURE_DECISIONS.md`.
3. Ne pas demarrer une feature sans demande explicite.
4. En cas de feature backend, verifier systematiquement l'isolation `organization_id`.
5. En cas de feature frontend, respecter les roles `admin` / `member`.
6. En cas de source d'avis, distinguer source active, source preparee et vrai connecteur.
7. En cas de modele IA, ne pas committer `app/models/sentiment_model.pkl` sans intention explicite.

## Prochaines evolutions produit possibles

Ces pistes ne font pas partie de cette tache documentaire :

- vrai connecteur Google Business Profile si le cadre API est clair ;
- connecteur Zendesk via API ;
- monitoring applicatif ;
- backups PostgreSQL ;
- meilleur systeme de roles ;
- tests frontend ;
- decomposition du gros `frontend/src/App.tsx` ;
- migration schema avec outil dedie ;
- durcissement auth production.

## Git

Ne pas commit/push automatiquement.

Apres cette tache documentaire, le working tree doit contenir uniquement des modifications de documentation sauf decision utilisateur contraire.

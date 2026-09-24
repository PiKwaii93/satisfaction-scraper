# Current Task

## État au 22 septembre 2026

La branche de travail est `main`. Les chantiers 1 à 10 de préparation à la
soutenance ont été validés. Les migrations de la base réelle sont à la révision
`20260921_0008`, et le modèle MLflow v53 a été promu après évaluation propre.
Le déploiement et le rollback sur la VM scolaire de test ont été exercés ; le
premier contrôle manuel de supervision a réussi.

Le chantier documentaire actuel relie les exigences aux preuves et à leurs
limites dans [docs/TRACEABILITY.md](docs/TRACEABILITY.md), détaille les runs
dans [docs/DEVOPS_EVIDENCE.md](docs/DEVOPS_EVIDENCE.md) et décrit
l'exploitation dans [docs/TEST_VM_RUNBOOK.md](docs/TEST_VM_RUNBOOK.md).

## Point ouvert

Le scheduler GitHub a maintenant produit un [heartbeat planifié réussi](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35765192366)
et un [événement Monitor planifié](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35764642522)
dont le job a été `skipped` par le garde. Le workflow heartbeat de diagnostic a été retiré ;
le cron final de Monitor est horaire à la minute 17. `TEST_MONITOR_SCHEDULE_ENABLED` reste
à `false` et n'a pas été activé pour une sonde planifiée réelle. La création d'événements `schedule`
est démontrée, **pas** l'exécution d'une sonde VM planifiée.

Les sources académiques Markdown et leurs rendus PPTX/PDF/DOCX sont indexés
dans [deliverables/README.md](deliverables/README.md). Le schéma détaillé et
l'ETL figurent dans [docs/SCHEMA_DONNEES_ETL.md](docs/SCHEMA_DONNEES_ETL.md).
La collecte directe de plus de 10 000 avis reste non conforme à la preuve
demandée. Les captures du registre MLflow v53 restent à constituer.

## Contraintes durables

- Ne pas refactorer globalement `frontend/src/App.tsx` sans demande explicite.
- Respecter l'isolation par `organization_id` et les rôles `admin` / `member`.
- Ne pas présenter une source préparée comme un connecteur fonctionnel.
- Ne pas committer de secrets, d'archives de base ou de clés SSH.
- Ne pas modifier la VM scolaire ou ses ressources MicroK8s sans demande explicite.
- Ne pas committer ou pousser sans autorisation utilisateur ; le chantier 12
  doit être revu avant tout commit ou push.

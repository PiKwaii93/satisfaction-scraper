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

Le scheduler GitHub n'a produit aucun run `schedule` observé au dernier
contrôle du 22/09/2026. Les crons de diagnostic sont temporairement à cinq
minutes, et `TEST_MONITOR_SCHEDULE_ENABLED` reste déclaré à `false`. Le
heartbeat diagnostic attend également une preuve de déclenchement. Ne pas
assimiler un workflow configuré à une exécution planifiée réussie.

## Contraintes durables

- Ne pas refactorer globalement `frontend/src/App.tsx` sans demande explicite.
- Respecter l'isolation par `organization_id` et les rôles `admin` / `member`.
- Ne pas présenter une source préparée comme un connecteur fonctionnel.
- Ne pas committer de secrets, d'archives de base ou de clés SSH.
- Ne pas modifier la VM scolaire ou ses ressources MicroK8s sans demande explicite.
- Ne pas committer ou pousser sans autorisation utilisateur ; le présent
  chantier documentaire est explicitement autorisé à être committé et poussé.

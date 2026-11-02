# Preuves DevOps pour la soutenance

Preuves initiales établies le 22 septembre 2026, complétées par une mesure de déploiement le 30 septembre 2026. Les liens GitHub pointent vers des runs réels. Les contrôles effectués manuellement sur la VM sont signalés comme tels ; ils ne sont pas présentés comme des jobs Actions. Aucune adresse publique, clé privée ou valeur de secret n'est conservée ici.

## CI et reproductibilité

| Élément | Preuve | Portée |
| --- | --- | --- |
| Révision de référence | `96af50594b55e4f4f45c978b0ebaa8febf720a7b` | État du code lors de la validation initiale. |
| CI automatique | [Run 35652347316](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35652347316) | 136 tests backend, 34 tests frontend et build Docker réussis à cette date. |
| E2E manuel | [Run 35652549430](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35652549430) | Stack Compose isolée, authentification, import CSV de 15 avis, run terminé et synthèse vérifiée par [verify_e2e.py](../scripts/verify_e2e.py). |

Le script [verify-repro.ps1](../scripts/verify-repro.ps1) utilise un projet Compose temporaire isolé. Dans [ci.yml](../.github/workflows/ci.yml), `e2e-smoke` s'exécute sur les push vers `main` après succès de `backend-tests`, `frontend-build` et `docker-build` ; il reste déclenchable via `workflow_dispatch` et ignoré sur `pull_request`. En CI, son mode smoke ne répète pas les suites backend/frontend déjà validées ; sans option, le script conserve la vérification complète. Le nombre de tests ci-dessus décrit **ce run manuel historique**, pas nécessairement la taille actuelle de la suite ni un run automatique du nouveau workflow.

## Préparation et déploiement de la VM existante

Le playbook [prepare-test-vm.yml](../deploy/prepare-test-vm.yml) a donné `ok=4 changed=1 unreachable=0 failed=0` au premier passage depuis WSL, puis `ok=4 changed=0 unreachable=0 failed=0` au second. Dans le premier déploiement Actions, il a de nouveau donné `changed=0`. Les permissions constatées étaient `750` pour le répertoire racine et `releases`, `700` pour `shared`. Docker et Compose étaient disponibles ; les ressources scolaires préexistantes, dont MicroK8s, sont restées intactes. Ces contrôles WSL sont des observations manuelles rapportées par l'équipe ; les logs Actions apportent la trace du passage automatisé.

| Déploiement automatique | SHA | Résultat |
| --- | --- | --- |
| [Run 35712061341](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35712061341) | `72517acbf156efab454e6496670b67526b109c3f` | Succès : archive du SHA, Ansible, build/démarrage Compose, API et frontend vérifiés. |
| [Run 35716640160](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35716640160) | `a50c69836f3117c224c017af84456e8ec2e1461b` | Second succès et mise à jour de `current.sha`. |
| [Run 36788014928](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/36788014928) | `a890033e4b178bb1a56d1de28618662372812df4` | Succès après restauration d'une baseline saine ; remplacement réel de l'API et mesure indépendante de sa disponibilité. |

L'API a répondu `{"status":"ok","database":"ok"}` ; PostgreSQL, Redis, MLflow, API et frontend étaient healthy, Celery actif. Une connexion à l'application via tunnel SSH a été validée manuellement. Le second SHA provient d'un **commit vide** créé pour éprouver le suivi des versions, sans changement fonctionnel de l'application.

## Rollback manuel

Après le second déploiement, le rollback exécuté sur la VM a rendu `DEPLOYED_SHA=72517acbf156efab454e6496670b67526b109c3f` et `HEALTHCHECK=passed`. Les marqueurs ont été inversés : `current.sha` est revenu à `72517ac...`, `previous.sha` à `a50c698...`. L'API et la base répondaient encore. C'est une preuve manuelle rapportée par l'équipe ; [test-deploy.sh](../deploy/test-deploy.sh) et ses [tests isolés](../deploy/test-deploy-tests.sh) décrivent le mécanisme.

Le rollback démontré revient entre **deux révisions Git**, dont la seconde est vide. Le retour de fonctionnalités distinctes, le downgrade d'une migration PostgreSQL et le rollback automatique après un candidat réellement défaillant n'ont pas été démontrés sur la VM. Le script ne supprime pas les volumes et ne restaure pas la base.

## Interruption mesurée pendant un déploiement réel

La [preuve de downtime](DEPLOYMENT_DOWNTIME_EVIDENCE.md) distingue l'indisponibilité initiale de la VM, la restauration des mêmes conteneurs sans rebuild, puis la mesure du déploiement normal [36788014928](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/36788014928). Sur la fenêtre mesurée, 20 des 313 sondes API ont échoué ; de la première panne au premier succès suivi de trois succès consécutifs, l'interruption observée a duré **21,177 s**. Les 320 sondes frontend ont toutes rendu HTTP 200 : aucune interruption observée à la résolution nominale d'environ une seconde. Le workflow a réussi, l'API et Celery ont été recréés, et le rollback n'a pas été utilisé. Cette preuve satisfait l'exigence de limitation documentée des interruptions sur la VM de test, sans revendiquer un déploiement blue/green ni un SLA.

## Tests de résilience isolés

La commande `python scripts/verify_resilience.py` a été exécutée localement
sur un projet Compose temporaire distinct de la stack habituelle. Les pannes
ci-dessous n'ont pas été provoquées sur la VM. Le script vérifie aussi le
nettoyage de ses conteneurs, réseaux, volumes et images propres au projet.

| Dépendance | Panne et reprise observées | Durée observée |
| --- | --- | --- |
| PostgreSQL | `/health` a rendu HTTP 503 avec « PostgreSQL indisponible. » ; après redémarrage, HTTP 200 et lecture métier réussie. | 4,84 s de l'arrêt au constat du 503 ; reprise en 5,59 s. |
| Worker Celery | Import accepté, run `pending` et API disponible sans worker ; après redémarrage, run `completed`, 15 avis distincts, résumé, KPI et distribution présents. Aucune duplication observée dans ce scénario. | 14,64 s. |
| Redis au dispatch | Avant correction, la sonde n'obtenait aucune réponse en 15 s alors que le run avait déjà été placé en `pending`. Après correction : publication sans retry, erreur broker interceptée, HTTP 503 avec message générique et run `failed`. Après retour de Redis, un nouvel import s'est terminé. | Refus en 5,03 s ; scénario et reprise en 11,88 s. |
| `model_bootstrap` | Dans un autre projet isolé, chemin d'empreinte inexistant : sortie 1 et API non démarrée. Le modèle versionné n'a pas été modifié. | 21,53 s, nettoyage compris. |

La matrice principale a duré **59,38 s avant nettoyage**. Aucun conteneur,
réseau, volume ou image spécifique au projet temporaire ne subsistait après
nettoyage. Les [tests du dispatch](../tests/test_job_dispatch_failure.py)
vérifient l'état `failed` et l'absence de détail sensible du broker dans la
réponse. Ces scénarios ne démontrent ni haute disponibilité, ni garantie de
traitement « exactly once ». Une coupure de MLflow après chargement du modèle
n'a pas été simulée : le parcours CSV testé utilise le modèle déjà chargé.

## Récupération applicative isolée

La commande `python scripts/verify_application_recovery.py` a été exécutée sur
une autre stack Compose temporaire. Un CSV vide ou blanc a rendu HTTP 400 en
preview et en import, sans créer de run ni envoyer de tâche. Une preview avec
colonne obligatoire absente ou en-tête seul a rendu HTTP 200 avec
`error_message` et zéro avis, conformément au contrat existant ; l'import
correspondant a rendu HTTP 400. Les mappings JSON invalides ont rendu HTTP 400.

Un second import identique pendant `pending` a rendu HTTP 409, avec un seul run.
Avant correction, `/execute` acceptait ce run actif en HTTP 200 et le
redispatchait. Après correction, il rend HTTP 409 : la mise à jour SQL
conditionnelle protège atomiquement `pending` et `running`, avant tout reset
des événements ou envoi Celery. Le cas `running` a été couvert par test ciblé,
sans être forcé en observation live. Un run `completed` a été relancé sur le
même identifiant, avec 15 avis distincts ; une nouvelle analyse après
`completed` a également réussi.

Dans le volume temporaire uniquement, le JSON d'un import CSV de test a été
momentanément rendu indisponible. Le run est passé à `failed` ; l'API est restée
saine, son événement d'échec était lisible et le message persisté ne contenait
pas le chemin interne. Après restauration du fichier, une nouvelle analyse a
réussi ; la relance du run échoué avec `skip_scrape=true` a terminé ce **même**
run en `completed`, avec 15 avis distincts et sans ancienne erreur affichée.
Un [test backend](../tests/test_analysis_run_recovery.py) simule séparément une
erreur de scraper : l'exception détaillée reste disponible au worker, tandis
que le run et ses événements reçoivent un message assaini. Aucun appel réel à
Trustpilot n'a été nécessaire.

La matrice a duré **56,02 s avant nettoyage** ; aucune ressource temporaire du
projet ne subsistait. La navigation du scraper est bornée à 60 s, mais aucune
limite globale de durée d'un run métier n'est démontrée. Les 120 s du smoke
E2E bornent le test, pas le produit. Ces observations ne prouvent pas une
garantie de traitement « exactly once ».

## KPI DevOps mesurés sur GitHub Actions

La source est l'historique du workflow [Deploy test VM](../.github/workflows/deploy-test.yml), lisible par [deployment_kpis.py](../scripts/deployment_kpis.py) avec une période ou une limite de runs. **Deployment Cycle Time** va du `workflow_dispatch` à la fin réussie de l'étape `Deploy and check API and frontend` ; la durée totale du workflow est une mesure distincte.

| KPI | Mesure du 22/09/2026 | Interprétation |
| --- | --- | --- |
| Deployment Cycle Time | 366 s pour `72517ac...` ; 63 s pour `a50c698...` | Deux déploiements réussis, même définition de début et de fin. |
| Deployment Frequency | 2 déploiements automatisés réussis | Journée UTC du 22/09/2026 ; le rollback manuel n'est pas compté. |
| Deployment Success Rate brut | 2 succès / 4 déclenchements = 50 % | Inclut les deux tentatives initiales échouées. |
| Deployment Success Rate après correction d'accès | 2 / 2 = 100 % | Sous-ensemble contextuel, pas remplacement du taux brut. |

Les deux premiers échecs ([35711099951](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35711099951), [35711897415](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35711897415)) ont eu lieu à l'étape Ansible pour accès SSH/configuration de clé, **avant transfert et activation de l'application**. Ils ne prouvent pas qu'une mauvaise version a été servie. Aucune valeur de secret n'est sortie par le script KPI.

## Supervision, alertes et remédiation

Le code de supervision avec traçabilité des incidents récupérés est présent dans le commit `ba50f8d1c081805efcc3ea519921c1b54b8c9137` et [monitor-test-vm.py](../deploy/monitor-test-vm.py). Le premier contrôle réel a été lancé manuellement : [run 35726582579](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35726582579), résultat `success`. Son artefact `test-vm-monitor-35726582579` contient `monitor-report.json`.

| Signal dans ce rapport | Résultat observé |
| --- | --- |
| SHA effectivement servi | `72517acbf156efab454e6496670b67526b109c3f` |
| SSH | `ok` |
| PostgreSQL, Redis, MLflow, API, frontend | `healthy` chacun |
| Celery | Conteneur `running`, `inspect ping` réussi |
| API HTTP, frontend HTTP | `true`, `true` |
| Disque `/` | Environ 11,82 GiB libres |
| Alerte, remédiation, résultat | `null`, `null`, `healthy` |

Lors de ce contrôle historique, le SHA servi était antérieur à `main` parce que la VM avait été volontairement rollbackée. Depuis le run 36788014928, `current.sha` correspond au SHA cible déployé. La sonde lit `current.sha` : elle rapporte l'état réel, pas nécessairement le dernier commit du dépôt. [monitor-test.yml](../.github/workflows/monitor-test.yml) publie un Step Summary et un JSON. Deux échecs applicatifs espacés de 30 secondes peuvent provoquer **un seul** restart de l'API ou du frontend si leurs dépendances sont saines. Un incident récupéré reste `alert` et la sonde post-restart est archivée ; un échec persistant reste `incident`. Sous 5 GiB libres, alerte sans remédiation. Aucune panne volontaire ni remédiation réelle n'a été provoquée sur la VM scolaire.

## Scheduler : événements démontrés, sonde VM planifiée en attente

Le constat initial du 22/09/2026 (« aucun run `schedule` observé ») est **périmé**. Depuis, le [heartbeat planifié 35765192366](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35765192366) a réussi et le [run Monitor planifié 35764642522](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/35764642522) a été créé. Son job a été `skipped` conformément au garde `TEST_MONITOR_SCHEDULE_ENABLED == 'true'` du [workflow](../.github/workflows/monitor-test.yml). La création d'événements par GitHub est donc démontrée ; **aucune sonde planifiée active de la VM n'est encore démontrée**. Le contrôle manuel sain 35726582579 reste une preuve distincte.

Le workflow heartbeat de diagnostic a été retiré après cette preuve. Le cron final de Monitor est horaire à la minute 17. `TEST_MONITOR_SCHEDULE_ENABLED` reste à `false` : un événement planifié peut créer un run GitHub `skipped` sans aucune supervision de VM exécutée.

## Limites à annoncer au jury

- L'[artefact HTTP 403 Showroomprivé](../data/evidence/trustpilot_showroomprive_representative.json) reste une tentative historique sans avis extraits. La [preuve Vapoter assainie](TRUSTPILOT_VAPOTER_EVIDENCE.md) démontre séparément 11 281 IDs uniques sur les vues accessibles ; elle ne constitue pas un test du déploiement ou du pipeline produit.
- Le rollback de migration DB, la remise en service de fonctionnalités différentes et l'auto-rollback provoqué sur VM n'ont pas été démontrés.
- `celery inspect ping` prouve la réponse du worker au moment de la sonde, pas le succès de toutes les tâches métier.
- GitHub Actions donne une supervision de **test**, sans garantie de cadence ni SLA de production ; les événements `schedule` sont prouvés, mais pas une sonde planifiée active de la VM.
- L'IP publique de la VM scolaire est dynamique ; la VM existe déjà, et le projet ne la provisionne pas.

Voir [TEST_VM_RUNBOOK.md](TEST_VM_RUNBOOK.md) pour les opérations et [TRACEABILITY.md](TRACEABILITY.md) pour le lien entre sujet, code et preuves.

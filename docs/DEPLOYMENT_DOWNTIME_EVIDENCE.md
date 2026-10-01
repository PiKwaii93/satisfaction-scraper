# Mesure de l'interruption lors d'un déploiement sur la VM de test

Mesure réalisée le 30 septembre 2026 (UTC) avec le workflow existant [Deploy test VM, run 36788014928](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/36788014928). Le workflow s'est terminé avec succès et a déployé `a890033e4b178bb1a56d1de28618662372812df4` depuis `main`, dont la [CI push 36745467908](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/36745467908) était verte.

## Périmètre et baseline

Avant le test, la stack avait été trouvée indisponible après un redémarrage de la VM : seul PostgreSQL, configuré avec `restart: always`, était revenu automatiquement. Les conteneurs existants ont été redémarrés sans build ni recréation. Cette indisponibilité **précède la mesure** et n'entre dans aucun calcul ci-dessous. Sa cause probable est la différence de politique de redémarrage ; aucune cause plus précise n'est démontrée.

La baseline était stable avant le workflow : API `/health` et frontend `/` répondaient HTTP 200, PostgreSQL, Redis, MLflow, API et frontend étaient `healthy`, et le worker Celery répondait à `inspect ping`. Le marqueur `current.sha` valait `72517acbf156efab454e6496670b67526b109c3f` et `previous.sha` valait `a50c69836f3117c224c017af84456e8ec2e1461b`. Les sondes avaient chacune 13 réponses saines avant le déclenchement.

## Protocole

Deux processus indépendants sur la VM ont interrogé environ chaque seconde `http://127.0.0.1:8000/health` et `http://127.0.0.1:5173/`. Chaque ligne privée contient `timestamp_utc,service,http_code,latency_s,curl_exit`. Les sondes ont commencé avant le workflow et ont continué pendant Ansible, le transfert de release, le build, le remplacement Compose et plusieurs réponses saines après le retour de l'application. Les CSV bruts ne sont pas publiés.

La première mesure date de 22:51:47 UTC pour les deux services. Le workflow a été déclenché à 22:52:17 UTC. Les dernières mesures datent de 22:57:34 UTC, après son succès à 22:56:50 UTC.

Le downtime observé est l'intervalle entre la première sonde non saine et la première réponse saine suivie de trois réponses saines consécutives. Une sonde saine exige HTTP 200 et un code de sortie cURL nul. La moyenne de latence ne porte que sur les sondes saines ; le maximum couvre toutes les sondes.

| Service | Sondes | Saines | Échecs | Première sonde non saine (UTC) | Première réponse saine et début de 3 succès consécutifs (UTC) | Downtime observé | Latence moyenne saine | Latence maximale |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| API | 313 | 293 | 20 | 22:56:26.622 | 22:56:47.799 | 21,177 s | 0,0453 s | 0,2054 s |
| Frontend | 320 | 320 | 0 | Aucune | Sans objet | Aucune interruption observée à la résolution nominale d’environ 1 seconde. | 0,0079 s | 0,1594 s |

Les 20 échecs API ont tous rendu le code HTTP `000` : 14 sorties cURL `7`, 5 sorties `56` et 1 sortie `52`. La première réponse saine après l'incident API est également la première d'une séquence de trois succès. Les plus grands intervalles entre deux mesures étaient de 1,612 s pour l'API et 1,584 s pour le frontend.

## Bascule et résultat

Le workflow a vérifié le SHA et la CI, préparé la VM avec Ansible, transféré l'archive Git immuable, construit les images applicatives avant la bascule, puis exécuté `docker compose up -d --no-build --wait` et les contrôles HTTP du script [test-deploy.sh](../deploy/test-deploy.sh). Aucun `docker compose down` global préalable n'a eu lieu. Le mécanisme de retour arrière applicatif existant était disponible ; il n'a pas été utilisé dans ce run.

Les IDs de conteneurs ont changé pour l'API, Celery, PostgreSQL et `model_bootstrap` ; ceux du frontend, de MLflow et de Redis sont restés identiques. La recréation d'au moins un service applicatif est donc démontrée. Après le workflow, l'API et le frontend répondaient HTTP 200 ; `current.sha` valait `a890033e4b178bb1a56d1de28618662372812df4` et `previous.sha` valait `72517acbf156efab454e6496670b67526b109c3f`.

Cette mesure montre une interruption API finie et observée de 21,177 s pendant un déploiement réel. La construction avant remplacement, l'absence d'arrêt global préalable, les healthchecks et le rollback applicatif limitent et encadrent la fenêtre d'indisponibilité. Le frontend est resté disponible à la résolution des sondes, sans garantie théorique de zéro interruption. Il s'agit d'un déploiement Compose mono-instance, **pas d'une architecture blue/green**. Le contrôle HTTP du frontend et `/health` ne prouve pas la continuité de tous les parcours métier, et un seul déploiement ne définit pas un SLA.

> Le mécanisme actuel limite l’interruption sans l’éliminer. Lors du déploiement mesuré sur la VM de test, l’API a connu une indisponibilité observée de 21,177 secondes tandis qu’aucune interruption du frontend n’a été observée à la résolution nominale d’environ une seconde. Cette mesure ne constitue ni une architecture blue/green ni une garantie de zéro interruption.

Améliorations futures possibles, sans constituer un écart obligatoire pour ce MVP : ajuster les politiques de redémarrage afin que les services applicatifs reviennent après un reboot de VM ; à plus grande échelle, envisager plusieurs instances avec bascule de trafic pour réduire davantage la fenêtre d'indisponibilité.

# Current Task

## Phase au 3 novembre 2026 : consolidation finale et freeze

Le candidat fonctionnel `f99789099fc3fa16a0c6cc2e0537e00eafc56776` a
passé l'audit de reproductibilité depuis une archive Git propre (10A), la
[CI push 41608401904](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/41608401904)
et le [déploiement officiel 41639303247](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/41639303247)
sur la VM de test (10B). Le smoke CSV réel de 15 avis et le snapshot applicatif
ont réussi sur la release servie.

Le [Monitor 41646917782](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/41646917782)
a détecté une véritable alerte de disque sous 5 GiB, avec l'application saine.
Après maintenance manuelle non destructive, le [Monitor 41662964180](https://github.com/PiKwaii93/satisfaction-scraper/actions/runs/41662964180)
a confirmé le retour à `healthy`. Ces deux runs démontrent l'intégration 9B
sur la VM. Leur détail et leurs limites figurent dans
[docs/DEVOPS_EVIDENCE.md](docs/DEVOPS_EVIDENCE.md) et
[docs/TRACEABILITY.md](docs/TRACEABILITY.md).

Le lot 10C consolide ces preuves et audite la documentation, sans changement
fonctionnel. Après ce lot, le projet entre en **freeze fonctionnel** : aucune
nouvelle feature, refonte ou modification ML ; seules des corrections bloquantes
démontrées pourront être examinées. La soutenance sera préparée séparément.

## Distinctions à conserver

- Le bootstrap d'un registre MLflow vierge crée une v1 ; il ne reconstitue pas
  le registre historique privé où le modèle retenu est v53.
- La collecte privée Vapoter établit 11 281 IDs uniques sur 16 vues parcourues
  jusqu'à leur fin naturelle, sans représenter un instantané simultané.
- Le Monitor planifié est encore gardé par `TEST_MONITOR_SCHEDULE_ENABLED` ;
  les preuves 9B sur VM sont deux exécutions **manuelles**.
- La VM pédagogique peut changer d'IP après arrêt/redémarrage. Après reboot,
  seule la politique `restart: always` de PostgreSQL a assuré son retour ;
  les autres conteneurs ont nécessité un redémarrage contrôlé, sans rebuild.
- Le commit documentaire final fera avancer `main` sans changer le code servi.
  Ne pas redéployer automatiquement ce nouveau SHA.

Voir [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) pour les évolutions futures hors
freeze et [docs/TEST_VM_RUNBOOK.md](docs/TEST_VM_RUNBOOK.md) pour l'exploitation.

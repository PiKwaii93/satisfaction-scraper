# Comparaison locale des variantes de classification

Expérience exécutée localement le 30 septembre 2026, sans accès à la VM, sans écriture dans MLflow et sans modification du modèle de production. Le [résumé JSON assaini](../data/evidence/ml_optimization_summary.json) contient les paramètres et les métriques numériques ; aucun verbatim ni identifiant individuel n'y figure.

## Données et protocole

Le snapshot local privé `data/training/sentiment_training_dataset.csv` compte 1 554 lignes : 1 514 annotations manuelles et 40 retours humains. Son SHA-256 **physique** est `f1f97241a5bd3da44a3ddc9abdc412e618a495350c44979d2092bb8b0dac85a2`. Après restauration des types d'identifiants utilisés avant l'export CSV, son empreinte **logique** calculée par `compute_training_dataset_hash()` est `deb2f21da31b6c64c999fd539b79192e26d2fd1c71e820f31884294c0e9984cd`, identique à celle publiée pour v53. Cette égalité porte sur les colonnes hachées par cette fonction ; elle ne signifie pas que le SHA-256 physique du CSV soit celui du run.

La déduplication globale précède le split ; le snapshot est déjà dédupliqué et retire 0 ligne supplémentaire. Split stratifié 80/20 avec `random_state=42` : 1 243 lignes d'entraînement et 311 de test. Les cinq variantes partagent le TF-IDF bigrammes (`min_df=2`, `sublinear_tf=True`), la régression logistique équilibrée et le poids feedback ×6. La seule dimension testée est l'usage et la pondération one-hot de la note. Une validation croisée stratifiée à trois plis sur l'entraînement classe les candidats par **macro-F1 moyen**. Le test final reste à l'écart de la sélection et n'est évalué qu'une fois, sur le candidat classé premier. Aucun modèle n'est enregistré ou promu.

## Résultats de validation interne

| Rang | Variante | Poids note | Macro-F1 | Weighted-F1 | Accuracy | F1 Négatif | F1 Neutre | F1 Positif |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Texte + note | 1,00 | 0,806412 | 0,899633 | 0,889770 | 0,903546 | 0,551984 | 0,963706 |
| 2 | Texte + note | 0,50 | 0,804235 | 0,899193 | 0,889772 | 0,903936 | 0,545064 | 0,963706 |
| 3 | Texte + note, configuration v53 | 0,25 | 0,804044 | 0,903538 | 0,899430 | 0,914985 | 0,532598 | 0,964548 |
| 4 | Texte + note | 0,10 | 0,727754 | 0,861577 | 0,872084 | 0,892022 | 0,362882 | 0,928358 |
| 5 | Texte seul | — | 0,651444 | 0,801837 | 0,816584 | 0,845936 | 0,241679 | 0,866716 |

Le poids 1,00 devance 0,25 de **0,002368** point de macro-F1 moyen ; la variation entre plis (écart-type 0,036666 pour 1,00, contre 0,019440 pour 0,25) est bien plus grande. La configuration 0,25 a de meilleures moyennes de weighted-F1 et d'accuracy. Les données montrent qu'une pondération de la note améliore nettement le texte seul dans ce protocole, mais ne démontrent **pas** que 1,00 soit durablement supérieur à 0,25.

## Test final du seul candidat sélectionné

Le poids 1,00, sélectionné sans consulter le test, obtient sur 311 exemples : macro-F1 **0,743568**, weighted-F1 **0,853967**, accuracy **0,836013** ; F1 Négatif **0,860465**, Neutre **0,444444**, Positif **0,925795**. Matrice de confusion, lignes vraies et colonnes prédites dans l'ordre Négatif, Neutre, Positif :

| Vrai / prédit | Négatif | Neutre | Positif |
| --- | ---: | ---: | ---: |
| Négatif | 111 | 28 | 4 |
| Neutre | 2 | 18 | 7 |
| Positif | 2 | 8 | 131 |

Le run v53 publié, avec la pondération 0,25, affiche sur son test final : **accuracy 0,842444**, **macro-F1 0,745860** et **weighted-F1 0,858162**. Le même snapshot logique et le split v53 (`random_state=42`, 1 243/311, mêmes effectifs par classe) ont été retrouvés : les résultats finaux peuvent donc être rapprochés comme constats sur ce protocole. Le candidat 1,00 obtient respectivement **0,836013**, **0,743568** et **0,853967** ; il ne démontre pas de gain sur ces trois métriques. Cette expérience **n'a pas réévalué 0,25 sur le test** : ses hyperparamètres ont été choisis exclusivement par validation croisée sur le train. Les chiffres du test, une fois observés, ne doivent pas servir à relancer une sélection opportuniste sur le même test. Le score Neutre demeure faible et visible.

**Conclusion académique :** « Une recherche contrôlée de paramètres a été menée sur le snapshot logique du run v53, avec sélection par validation croisée stratifiée sur le jeu d’entraînement. Les écarts entre les meilleures variantes sont faibles et le candidat sélectionné n’a pas démontré d’amélioration suffisamment robuste sur l’évaluation finale pour justifier le remplacement de v53. Le modèle v53 a donc été conservé en production. » Aucun entraînement de v54, enregistrement de modèle ou changement d'alias MLflow n'a été effectué dans ce chantier.

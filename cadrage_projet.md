# Document de Cadrage : Projet "Satisfaction Client"

## 1. Introduction et Problématique
* **Contexte :** La supply chain représente les étapes d'approvisionnement, du processus productif et de distribution de la marchandise. L'évaluation de la satisfaction client est cruciale pour identifier des problèmes de conception, de livraison ou de durabilité.
* **Problématique :** Comment transformer des milliers de verbatims non structurés en indicateurs de performance (KPIs) actionnables pour aider à la décision et à la redirection des clients insatisfaits ?
* **Objectifs :**
    - Automatiser la collecte de données qualitatives (Web Scraping).
    - Centraliser et structurer les données (Pipeline ETL / PostgreSQL).
    - Fournir une synthèse visuelle (Dashboard Streamlit) et sémantique (NLP).

## 2. Analyse des parties prenantes (Personas)
| Persona | Besoin principal | Valeur ajoutée |
| :--- | :--- | :--- |
| **Responsable Supply Chain** | Identifier les récurrences de retards/problèmes de livraison. | Réduire le taux de litiges logistiques. |
| **Responsable Service Client** | Repérer rapidement les avis très négatifs pour réagir. | Améliorer le taux de rétention client. |
| **Analyste Data** | Disposer de données propres et centralisées. | Faciliter la prise de décision stratégique. |

## 3. KPIs Métier (Indicateurs clés)
Pour piloter notre solution, nous suivrons les indicateurs suivants :
1. **Note Moyenne Globale :** Indicateur de santé général de la satisfaction.
2. **Volume d'avis par thématique :** Répartition des problèmes (Produit vs Livraison vs SAV).
3. **Distribution du sentiment :** Analyse NLP pour quantifier la part d'avis positifs/négatifs.
4. **Indice de réactivité :** Taux de réponse de l'entreprise face aux avis négatifs.

## 4. Analyse des ressources (Cartographie)
* **Technique :** Docker, Python, PostgreSQL, Streamlit, Librairies NLP (TextBlob, Scikit-learn).
* **Humaines :** Binôme de projet (Développement & Data Engineering).
* **Données :** Scraping de sites publics, base de données relationnelle (PostgreSQL).

## 5. Roadmap de haut niveau
1. **Phase 1 (MVP) :** Automatisation du scraping + Pipeline ETL + Dashboard de visualisation.
2. **Phase 2 (Analyse) :** Implémentation du modèle NLP et versioning de modèle (MLFlow).
3. **Phase 3 (Production) :** Automatisation CI/CD (GitHub Actions), monitoring et alertes.

*Ce document sert de base au développement du MVP et sera mis à jour au fil des itérations.*
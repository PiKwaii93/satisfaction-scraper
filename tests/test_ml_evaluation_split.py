import unittest

import pandas as pd

from app.train_model import (
    EVALUATION_KEY_COLUMN,
    FEEDBACK_DATASET_SOURCE,
    MANUAL_DATASET_SOURCE,
    deduplicate_training_dataframe,
    split_training_dataframe,
)


def make_balanced_dataset(rows_per_class=30):
    rows = []
    for target in (0, 1, 2):
        for position in range(rows_per_class):
            rows.append(
                {
                    "id": f"{target}-{position}",
                    "verbatim": f"avis unique classe {target} numéro {position}",
                    "rating": target + 1,
                    "target": target,
                    "manual_label": ("Négatif", "Neutre", "Positif")[target],
                    "dataset_source": MANUAL_DATASET_SOURCE,
                }
            )
    return deduplicate_training_dataframe(pd.DataFrame(rows))


class MlEvaluationSplitTest(unittest.TestCase):
    def test_global_deduplication_prefers_feedback(self):
        dataframe = pd.DataFrame(
            [
                {
                    "id": "manual-1",
                    "verbatim": "  Livraison   rapide ",
                    "rating": 5,
                    "target": 2,
                    "manual_label": "Positif",
                    "dataset_source": MANUAL_DATASET_SOURCE,
                },
                {
                    "id": "manual-2",
                    "verbatim": "livraison rapide",
                    "rating": 5.0,
                    "target": 2,
                    "manual_label": "Positif",
                    "dataset_source": MANUAL_DATASET_SOURCE,
                },
                {
                    "id": "feedback-1",
                    "verbatim": "LIVRAISON RAPIDE",
                    "rating": "5",
                    "target": 1,
                    "manual_label": "Neutre",
                    "dataset_source": FEEDBACK_DATASET_SOURCE,
                },
            ]
        )

        result = deduplicate_training_dataframe(dataframe)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["id"], "feedback-1")
        self.assertFalse(result[EVALUATION_KEY_COLUMN].duplicated().any())

    def test_train_and_test_keys_are_disjoint(self):
        dataframe = make_balanced_dataset()

        train_df, test_df = split_training_dataframe(dataframe)

        self.assertTrue(
            set(train_df[EVALUATION_KEY_COLUMN]).isdisjoint(
                test_df[EVALUATION_KEY_COLUMN]
            )
        )

    def test_split_is_reproducible(self):
        dataframe = make_balanced_dataset()

        first_train, first_test = split_training_dataframe(
            dataframe, random_state=42
        )
        second_train, second_test = split_training_dataframe(
            dataframe, random_state=42
        )

        self.assertListEqual(first_train["id"].tolist(), second_train["id"].tolist())
        self.assertListEqual(first_test["id"].tolist(), second_test["id"].tolist())

    def test_split_preserves_balanced_class_distribution(self):
        dataframe = make_balanced_dataset()

        train_df, test_df = split_training_dataframe(
            dataframe, test_size=0.2, random_state=42
        )

        expected_distribution = {0: 1 / 3, 1: 1 / 3, 2: 1 / 3}
        self.assertDictEqual(
            train_df["target"].value_counts(normalize=True).sort_index().to_dict(),
            expected_distribution,
        )
        self.assertDictEqual(
            test_df["target"].value_counts(normalize=True).sort_index().to_dict(),
            expected_distribution,
        )


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report

from app import train_model


def make_mlflow_mock():
    mlflow_mock = Mock()
    mlflow_mock.start_run.return_value.__enter__ = Mock(return_value=None)
    mlflow_mock.start_run.return_value.__exit__ = Mock(return_value=False)
    mlflow_mock.active_run.return_value = SimpleNamespace(
        info=SimpleNamespace(run_id="run-123")
    )
    mlflow_mock.sklearn.log_model.return_value = SimpleNamespace(
        registered_model_version="7"
    )
    return mlflow_mock


class MlflowEvaluationPayloadTest(unittest.TestCase):
    def test_payload_contains_required_metrics_artifacts_and_dataset_hash(self):
        dataframe = pd.DataFrame(
            [
                {
                    "id": index,
                    "verbatim": f"avis {index}",
                    "rating": target + 1,
                    "target": target,
                    "dataset_source": train_model.MANUAL_DATASET_SOURCE,
                    "sample_weight": 1.0,
                }
                for index, target in enumerate([0, 1, 2, 0, 1, 2, 0, 1, 2])
            ]
        )
        dataframe.attrs["deduplication"] = {
            "rows_before": 11,
            "rows_after": 9,
            "removed_rows": 2,
            "duplicate_groups": 1,
        }
        train_df = dataframe.iloc[:6]
        test_df = dataframe.iloc[6:]
        y_test = test_df["target"]
        y_pred = pd.Series([0, 2, 2], index=y_test.index)
        report = classification_report(
            y_test,
            y_pred,
            labels=sorted(train_model.TARGET_TO_LABEL),
            target_names=train_model.TARGET_NAMES,
            output_dict=True,
            zero_division=0,
        )

        metrics, parameters, artifacts = train_model.build_mlflow_evaluation_payload(
            df=dataframe,
            train_df=train_df,
            test_df=test_df,
            y_test=y_test,
            y_pred=y_pred,
            evaluation_report=report,
            accuracy=accuracy_score(y_test, y_pred),
            random_state=42,
            test_size=0.2,
        )

        required_metrics = {
            "accuracy",
            "macro_f1",
            "weighted_f1",
            "train_examples",
            "test_examples",
            "dataset_duplicates_removed",
            "class_negatif_precision",
            "class_negatif_recall",
            "class_negatif_f1",
            "class_neutre_precision",
            "class_neutre_recall",
            "class_neutre_f1",
            "class_positif_precision",
            "class_positif_recall",
            "class_positif_f1",
        }
        self.assertTrue(required_metrics.issubset(metrics))
        self.assertEqual(metrics["dataset_rows_before_deduplication"], 11)
        self.assertEqual(metrics["dataset_rows_after_deduplication"], 9)
        self.assertEqual(parameters["random_state"], 42)
        self.assertEqual(parameters["test_size"], 0.2)
        self.assertEqual(len(parameters["dataset_sha256"]), 64)
        self.assertSetEqual(
            set(artifacts),
            {
                "evaluation/confusion_matrix.json",
                "evaluation/classification_report.json",
                "dataset/dataset_info.json",
            },
        )

        same_hash = train_model.compute_training_dataset_hash(dataframe.copy())
        changed_dataframe = dataframe.copy()
        changed_dataframe.loc[0, "verbatim"] = "avis modifié"
        changed_hash = train_model.compute_training_dataset_hash(changed_dataframe)
        self.assertEqual(parameters["dataset_sha256"], same_hash)
        self.assertNotEqual(parameters["dataset_sha256"], changed_hash)


class MlflowPublicationStatusTest(unittest.TestCase):
    def test_logging_failure_is_explicit(self):
        mlflow_mock = make_mlflow_mock()
        mlflow_mock.log_metrics.side_effect = RuntimeError("tracking unavailable")

        with patch.object(train_model, "mlflow", mlflow_mock), patch.object(
            train_model, "MlflowClient"
        ):
            result = train_model.log_model_to_mlflow(
                model=object(),
                metrics={"accuracy": 0.75},
                parameters={"random_state": 42},
                artifacts={},
            )

        self.assertFalse(result["mlflow_logging_succeeded"])
        self.assertFalse(result["model_registration_succeeded"])
        self.assertFalse(result["production_alias_promotion_attempted"])
        self.assertFalse(result["mlflow_publication_succeeded"])
        self.assertEqual(result["mlflow_error_stage"], "mlflow_logging")
        self.assertIn("tracking unavailable", result["mlflow_error"])

    def test_success_distinguishes_all_publication_steps(self):
        mlflow_mock = make_mlflow_mock()
        client = Mock()

        with patch.object(train_model, "mlflow", mlflow_mock), patch.object(
            train_model, "MlflowClient", return_value=client
        ):
            result = train_model.log_model_to_mlflow(
                model=object(),
                metrics={"accuracy": 0.75},
                parameters={"random_state": 42},
                artifacts={"evaluation/report.json": {"ok": True}},
            )

        self.assertTrue(result["mlflow_logging_succeeded"])
        self.assertTrue(result["model_registration_succeeded"])
        self.assertTrue(result["production_alias_promotion_attempted"])
        self.assertTrue(result["production_alias_promotion_succeeded"])
        self.assertTrue(result["mlflow_publication_succeeded"])
        self.assertEqual(result["model_version"], "7")
        self.assertEqual(result["model_uri"], "models:/sentiment_model@production")
        mlflow_mock.log_metrics.assert_called_once_with({"accuracy": 0.75})
        mlflow_mock.log_params.assert_called_once_with({"random_state": 42})
        mlflow_mock.log_dict.assert_called_once_with(
            {"ok": True}, "evaluation/report.json"
        )
        client.set_registered_model_alias.assert_called_once_with(
            name="sentiment_model",
            alias="production",
            version="7",
        )

    def test_candidate_is_registered_without_alias_or_database_synchronization(self):
        mlflow_mock = make_mlflow_mock()
        client = Mock()

        with patch.object(train_model, "mlflow", mlflow_mock), patch.object(
            train_model, "MlflowClient", return_value=client
        ):
            publication = train_model.log_model_to_mlflow(
                model=object(),
                metrics={"accuracy": 0.75},
                parameters={"random_state": 42},
                artifacts={},
                promote_to_production=False,
            )
            with patch.object(
                train_model, "synchronize_database_predictions"
            ) as synchronize_mock:
                synchronized = (
                    train_model.synchronize_predictions_after_production_promotion(
                        model=object(),
                        publication_metadata=publication,
                    )
                )

        self.assertTrue(publication["mlflow_logging_succeeded"])
        self.assertTrue(publication["model_registration_succeeded"])
        self.assertFalse(publication["production_alias_promotion_attempted"])
        self.assertFalse(publication["production_alias_promotion_succeeded"])
        self.assertTrue(publication["mlflow_publication_succeeded"])
        self.assertEqual(publication["model_uri"], "models:/sentiment_model/7")
        client.set_registered_model_alias.assert_not_called()
        self.assertFalse(synchronized)
        synchronize_mock.assert_not_called()

    def test_registration_failure_is_reported_and_does_not_promote_alias(self):
        mlflow_mock = make_mlflow_mock()
        mlflow_mock.sklearn.log_model.side_effect = RuntimeError("registry unavailable")
        client = Mock()

        with patch.object(train_model, "mlflow", mlflow_mock), patch.object(
            train_model, "MlflowClient", return_value=client
        ):
            result = train_model.log_model_to_mlflow(
                model=object(),
                metrics={"accuracy": 0.75},
                parameters={"random_state": 42},
                artifacts={},
            )

        self.assertTrue(result["mlflow_logging_succeeded"])
        self.assertFalse(result["model_registration_succeeded"])
        self.assertFalse(result["production_alias_promotion_attempted"])
        self.assertFalse(result["production_alias_promotion_succeeded"])
        self.assertFalse(result["mlflow_publication_succeeded"])
        self.assertEqual(result["mlflow_error_stage"], "model_registration")
        self.assertIn("registry unavailable", result["mlflow_error"])
        client.set_registered_model_alias.assert_not_called()

    def test_alias_failure_preserves_successful_model_registration_status(self):
        mlflow_mock = make_mlflow_mock()
        client = Mock()
        client.set_registered_model_alias.side_effect = RuntimeError("alias unavailable")

        with patch.object(train_model, "mlflow", mlflow_mock), patch.object(
            train_model, "MlflowClient", return_value=client
        ):
            result = train_model.log_model_to_mlflow(
                model=object(),
                metrics={"accuracy": 0.75},
                parameters={"random_state": 42},
                artifacts={},
            )

        self.assertTrue(result["mlflow_logging_succeeded"])
        self.assertTrue(result["model_registration_succeeded"])
        self.assertTrue(result["production_alias_promotion_attempted"])
        self.assertFalse(result["production_alias_promotion_succeeded"])
        self.assertFalse(result["mlflow_publication_succeeded"])
        self.assertEqual(
            result["mlflow_error_stage"], "production_alias_promotion"
        )
        self.assertEqual(result["model_uri"], "models:/sentiment_model/7")


class ProductionPredictionSynchronizationTest(unittest.TestCase):
    def test_predictions_are_not_synchronized_when_promotion_failed(self):
        with patch.object(
            train_model, "synchronize_database_predictions"
        ) as synchronize_mock:
            synchronized = (
                train_model.synchronize_predictions_after_production_promotion(
                    model=object(),
                    publication_metadata={
                        "production_alias_promotion_succeeded": False
                    },
                )
            )

        self.assertFalse(synchronized)
        synchronize_mock.assert_not_called()

    def test_predictions_are_synchronized_after_successful_promotion(self):
        model = object()
        with patch.object(
            train_model, "synchronize_database_predictions"
        ) as synchronize_mock:
            synchronized = (
                train_model.synchronize_predictions_after_production_promotion(
                    model=model,
                    publication_metadata={
                        "production_alias_promotion_succeeded": True
                    },
                )
            )

        self.assertTrue(synchronized)
        synchronize_mock.assert_called_once_with(model)


if __name__ == "__main__":
    unittest.main()

"""
Evaluation Module
-----------------
Evaluates fall detection performance with subject-independent splitting.
Computes precision, recall, F1 for fall class and ablation studies.
"""

import numpy as np
import pandas as pd
from typing import Any, Tuple, Dict, List, Optional
import logging
from pathlib import Path
import json
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (
    classification_report, confusion_matrix, 
    f1_score, precision_score, recall_score, roc_auc_score
)

from project_config import load_config

# Import our modules
from model_rf import FallDetectionRF
# from model_cnn_lstm import FallDetectionCNNLSTM  # Uncomment when built

logger = logging.getLogger(__name__)

class FallDetectionEvaluator:
    """Evaluates fall detection models with proper validation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        self.config = load_config(config_path)
        
        logger.info("FallDetectionEvaluator initialized")
    
    def subject_independent_split(self, 
                                 df: pd.DataFrame,
                                 test_subjects: Optional[List[str]] = None,
                                 test_fraction: float = 0.2,
                                 random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data by subject ID to prevent data leakage.
        
        Args:
            df: DataFrame with features and subject_id column
            test_subjects: Specific subjects to use for test set (if None, random selection)
            test_fraction: Fraction of subjects to use for test set
            random_state: Random seed for reproducibility
            
        Returns:
            Tuple of (train_df, test_df)
        """
        if 'subject_id' not in df.columns:
            raise ValueError("DataFrame must contain 'subject_id' column")
        if not 0 < test_fraction < 1:
            raise ValueError("test_fraction must be between 0 and 1")
        
        unique_subjects = df['subject_id'].unique()
        n_subjects = len(unique_subjects)
        if n_subjects < 2:
            raise ValueError(
                "Subject-independent split requires at least two subject IDs; "
                f"received {n_subjects}."
            )
        
        if test_subjects is not None:
            # Use specified subjects for test
            test_subjects = [s for s in test_subjects if s in unique_subjects]
            if not test_subjects:
                raise ValueError("No valid test subjects were provided")
            train_subjects = [s for s in unique_subjects if s not in test_subjects]
            logger.info(f"Using specified test subjects: {test_subjects}")
        else:
            # Randomly select test subjects
            n_test = max(1, int(n_subjects * test_fraction))
            rng = np.random.default_rng(random_state)
            test_subjects = rng.choice(unique_subjects, size=n_test, replace=False).tolist()
            train_subjects = [s for s in unique_subjects if s not in test_subjects]
            logger.info(f"Randomly selected {len(test_subjects)} test subjects: {test_subjects}")
        
        train_df = df[df['subject_id'].isin(train_subjects)].copy()
        test_df = df[df['subject_id'].isin(test_subjects)].copy()
        
        logger.info(f"Split: {len(train_df)} train samples ({len(train_subjects)} subjects), "
                   f"{len(test_df)} test samples ({len(test_subjects)} subjects)")
        
        return train_df, test_df
    
    def evaluate_model(self, 
                      model: FallDetectionRF,
                      test_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Evaluate model on test set.
        
        Args:
            model: Trained FallDetectionRF model
            test_df: Test DataFrame with features and labels
            
        Returns:
            Dictionary of evaluation metrics
        """
        # Prepare test data
        X_test, y_test, _groups_test = model.prepare_features(test_df)
        y_test = np.asarray(y_test)
        if not set(np.unique(y_test)).issubset({0, 1}):
            raise ValueError("Evaluation currently requires binary labels encoded as 0/1")
        if len(np.unique(y_test)) < 2:
            raise ValueError("Evaluation test set must contain both fall and non-fall labels")

        # Predict from raw features. The model wrapper applies the fitted
        # scaler exactly once.
        y_pred = model.predict(X_test)[0]
        y_proba = model.predict_proba(X_test)[0]
        
        # Compute metrics
        metrics = {
            'accuracy': np.mean(y_pred == y_test),
            'precision': precision_score(y_test, y_pred, average='binary', zero_division=0),
            'recall': recall_score(y_test, y_pred, average='binary', zero_division=0),
            'f1': f1_score(y_test, y_pred, average='binary', zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_proba)
        }
        
        # Per-class metrics
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        metrics['per_class'] = report
        
        # Confusion matrix with an explicit binary label order.
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        metrics['confusion_matrix'] = {
            'tn': int(cm[0, 0]),
            'fp': int(cm[0, 1]),
            'fn': int(cm[1, 0]),
            'tp': int(cm[1, 1])
        }

        # Fall-class specific metrics (what we care about most).
        fall_report = report.get(1, report.get('1'))
        if fall_report is not None:
            metrics['fall_precision'] = fall_report['precision']
            metrics['fall_recall'] = fall_report['recall']
            metrics['fall_f1'] = fall_report['f1-score']
        else:
            metrics['fall_precision'] = 0.0
            metrics['fall_recall'] = 0.0
            metrics['fall_f1'] = 0.0
        
        logger.info(f"Evaluation results: F1={metrics['f1']:.3f}, "
                   f"Precision={metrics['precision']:.3f}, Recall={metrics['recall']:.3f}")
        
        return metrics
    
    def cross_validate_subject_independent(self,
                                          df: pd.DataFrame,
                                          n_splits: int = 5) -> Dict[str, Any]:
        """
        Perform subject-independent cross-validation.
        
        Args:
            df: DataFrame with features and labels
            n_splits: Number of CV folds
            
        Returns:
            Dictionary with CV results
        """
        logger.info(f"Starting {n_splits}-fold subject-independent cross-validation")
        
        # Prepare data
        X, y, groups = FallDetectionRF().prepare_features(df)
        
        # GroupKFold by subject ID
        n_subjects = len(np.unique(groups))
        if n_subjects < 2:
            raise ValueError("Cross-validation requires at least two subject IDs")
        if n_splits > n_subjects:
            raise ValueError(
                f"n_splits={n_splits} exceeds the number of subjects ({n_subjects})"
            )
        group_kfold = GroupKFold(n_splits=n_splits)
        
        fold_results = []
        
        for fold, (train_idx, test_idx) in enumerate(group_kfold.split(X, y, groups)):
            logger.info(f"Processing fold {fold+1}/{n_splits}")
            
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Create and train model
            model = FallDetectionRF()
            
            # Scale features
            X_train_scaled = model.scaler.fit_transform(X_train)
            X_test_scaled = model.scaler.transform(X_test)
            
            # Train
            model.model.fit(X_train_scaled, y_train)
            
            # Predict
            y_pred = model.model.predict(X_test_scaled)
            y_proba = model.model.predict_proba(X_test_scaled)[:, 1]
            
            # Compute metrics
            fold_metrics = {
                'fold': fold,
                'train_subjects': np.unique(groups[train_idx]).tolist(),
                'test_subjects': np.unique(groups[test_idx]).tolist(),
                'accuracy': np.mean(y_pred == y_test),
                'precision': precision_score(y_test, y_pred, average='binary', zero_division=0),
                'recall': recall_score(y_test, y_pred, average='binary', zero_division=0),
                'f1': f1_score(y_test, y_pred, average='binary', zero_division=0),
                'roc_auc': roc_auc_score(y_test, y_proba) if len(np.unique(y_test)) > 1 else 0.0,
                'fall_precision': None,
                'fall_recall': 0.0,
                'fall_f1': 0.0
            }
            
            # Fall-class metrics
            report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
            if '1' in report:
                fold_metrics['fall_precision'] = report['1']['precision']
                fold_metrics['fall_recall'] = report['1']['recall']
                fold_metrics['fall_f1'] = report['1']['f1-score']
            
            fold_results.append(fold_metrics)
            
            logger.info(f"Fold {fold+1}: F1={fold_metrics['f1']:.3f}, "
                       f"Fall F1={fold_metrics['fall_f1']:.3f}")
        
        # Aggregate results
        metrics_arrays = {
            'accuracy': [r['accuracy'] for r in fold_results],
            'precision': [r['precision'] for r in fold_results],
            'recall': [r['recall'] for r in fold_results],
            'f1': [r['f1'] for r in fold_results],
            'roc_auc': [r['roc_auc'] for r in fold_results],
            'fall_precision': [r['fall_precision'] for r in fold_results if r['fall_precision'] is not None],
            'fall_recall': [r['fall_recall'] for r in fold_results],
            'fall_f1': [r['fall_f1'] for r in fold_results]
        }
        
        cv_results = {
            'n_folds': n_splits,
            'fold_results': fold_results,
            'mean_accuracy': np.mean(metrics_arrays['accuracy']),
            'std_accuracy': np.std(metrics_arrays['accuracy']),
            'mean_precision': np.mean(metrics_arrays['precision']),
            'std_precision': np.std(metrics_arrays['precision']),
            'mean_recall': np.mean(metrics_arrays['recall']),
            'std_recall': np.std(metrics_arrays['recall']),
            'mean_f1': np.mean(metrics_arrays['f1']),
            'std_f1': np.std(metrics_arrays['f1']),
            'mean_roc_auc': np.mean(metrics_arrays['roc_auc']),
            'std_roc_auc': np.std(metrics_arrays['roc_auc']),
            'mean_fall_precision': np.mean(metrics_arrays['fall_precision']) if metrics_arrays['fall_precision'] else 0.0,
            'std_fall_precision': np.std(metrics_arrays['fall_precision']) if len(metrics_arrays['fall_precision']) > 1 else 0.0,
            'mean_fall_recall': np.mean(metrics_arrays['fall_recall']),
            'std_fall_recall': np.std(metrics_arrays['fall_recall']),
            'mean_fall_f1': np.mean(metrics_arrays['fall_f1']),
            'std_fall_f1': np.std(metrics_arrays['fall_f1'])
        }
        
        logger.info(f"CV Results: Fall F1 = {cv_results['mean_fall_f1']:.3f} ± {cv_results['std_fall_f1']:.3f}")
        
        return cv_results
    
    def ablation_study(self,
                      df: pd.DataFrame,
                      base_features: List[str]) -> Dict[str, Any]:
        """
        Perform ablation study to measure contribution of each feature/component.
        
        Args:
            df: DataFrame with features and labels
            base_features: List of all available feature names
            
        Returns:
            Dictionary with ablation results
        """
        logger.info("Starting ablation study")
        
        # Prepare data once
        X, y, groups = FallDetectionRF().prepare_features(df)
        X_scaled = FallDetectionRF().scaler.fit_transform(X)
        
        # Baseline: all features
        logger.info("Training baseline model with all features")
        base_model = FallDetectionRF()
        base_model.model.fit(X_scaled, y)
        base_pred = base_model.model.predict(X_scaled)
        base_f1 = f1_score(y, base_pred, average='binary', zero_division=0)
        
        logger.info(f"Baseline F1 (all features): {base_f1:.3f}")
        
        # Test each feature removal
        ablation_results = {
            'status': 'diagnostic_only',
            'warning': 'Feature ablation is fitted/evaluated in-sample; do not use as held-out performance.',
            'baseline': {
                'f1': base_f1,
                'features': base_features.copy(),
                'n_features': len(base_features)
            },
            'feature_ablation': {},
            'component_ablation': {}
        }
        
        # Feature ablation: remove one feature at a time
        for i, feature_to_remove in enumerate(base_features):
            if i % 10 == 0:  # Log progress
                logger.info(f"Feature ablation progress: {i+1}/{len(base_features)}")
            
            # Create feature set without this feature
            remaining_features = [f for f in base_features if f != feature_to_remove]
            
            if len(remaining_features) == 0:
                continue
            
            # Get column indices
            feature_indices = [base_features.index(f) for f in remaining_features]
            X_reduced = X_scaled[:, feature_indices]
            
            # Train and evaluate
            model = FallDetectionRF()
            model.model.fit(X_reduced, y)
            y_pred = model.model.predict(X_reduced)
            f1 = f1_score(y, y_pred, average='binary', zero_division=0)
            
            ablation_results['feature_ablation'][feature_to_remove] = {
                'f1': f1,
                'f1_drop': base_f1 - f1,
                'relative_drop': (base_f1 - f1) / base_f1 if base_f1 > 0 else 0.0,
                'n_features': len(remaining_features)
            }
        
        # Component ablation is intentionally not fabricated. Removing a
        # pipeline component requires a separately trained, held-out
        # experiment; simulated literature values must not be reported as
        # measurements.
        ablation_results['component_ablation'] = {
            'status': 'not_evaluated',
            'reason': 'Component-level held-out experiments have not been implemented.',
        }
        logger.info("Ablation study complete (feature-only results)")
    
    def compare_models(self,
                      rf_results: Dict[str, Any],
                      cnn_lstm_results: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Compare Random Forest and CNN-LSTM model results.
        
        Args:
            rf_results: Results from RF evaluation
            cnn_lstm_results: Results from CNN-LSTM evaluation (optional)
            
        Returns:
            DataFrame comparing model performance
        """
        comparison_data = []
        
        # Add RF results
        rf_row = {
            'model': 'Random Forest',
            'type': 'baseline',
            'accuracy': rf_results.get('accuracy', 0.0),
            'precision': rf_results.get('precision', 0.0),
            'recall': rf_results.get('recall', 0.0),
            'f1': rf_results.get('f1', 0.0),
            'fall_precision': rf_results.get('fall_precision', 0.0),
            'fall_recall': rf_results.get('fall_recall', 0.0),
            'fall_f1': rf_results.get('fall_f1', 0.0),
            'roc_auc': rf_results.get('roc_auc', 0.0)
        }
        comparison_data.append(rf_row)
        
        # Add CNN-LSTM results if provided
        if cnn_lstm_results is not None:
            cnn_row = {
                'model': 'CNN-LSTM',
                'type': 'stretch_goal',
                'accuracy': cnn_lstm_results.get('accuracy', 0.0),
                'precision': cnn_lstm_results.get('precision', 0.0),
                'recall': cnn_lstm_results.get('recall', 0.0),
                'f1': cnn_lstm_results.get('f1', 0.0),
                'fall_precision': cnn_lstm_results.get('fall_precision', 0.0),
                'fall_recall': cnn_lstm_results.get('fall_recall', 0.0),
                'fall_f1': cnn_lstm_results.get('fall_f1', 0.0),
                'roc_auc': cnn_lstm_results.get('roc_auc', 0.0)
            }
            comparison_data.append(cnn_row)
        
        df_comparison = pd.DataFrame(comparison_data)
        logger.info(f"Model comparison DataFrame created with {len(df_comparison)} models")
        
        return df_comparison
    
    def save_evaluation_results(self,
                               results: Dict[str, Any],
                               output_path: Path):
        """Save evaluation results to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert numpy types to Python types for JSON serialization
        def convert_for_json(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_for_json(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            else:
                return obj
        
        serializable_results = convert_for_json(results)
        
        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Evaluation results saved to {output_path}")

def evaluate_fall_detection(features_csv: str,
                           model_path: str = "models/rf_baseline.joblib",
                           config_path: str = "config.yaml",
                           output_json: str = "report/evaluation_results.json") -> Dict[str, Any]:
    """Evaluate a model on a held-out feature CSV.

    ``features_csv`` must be a test set produced from subjects/clips that were
    not used to train ``model_path``.  This function deliberately does not
    create a new split after loading a pre-trained model; doing so would leak
    test subjects into training.
    """
    df = pd.read_csv(features_csv)
    if 'subject_id' not in df.columns:
        raise ValueError("Evaluation data must contain subject_id")
    logger.info("Loaded held-out features from %s: %s rows", features_csv, len(df))

    evaluator = FallDetectionEvaluator(config_path)
    model = FallDetectionRF(config_path)
    model.load_model(Path(model_path))
    test_results = evaluator.evaluate_model(model, df)

    meta_cols = {'subject_id', 'clip_id', 'window_start', 'window_end',
                 'window_start_time', 'window_end_time', 'label', 'fall', 'activity'}
    feature_names = [col for col in df.columns if col not in meta_cols]
    final_results = {
        'dataset_info': {
            'total_samples': len(df),
            'n_features': len(feature_names),
            'subjects_total': int(df['subject_id'].nunique()),
            'clips_total': int(df['clip_id'].nunique()) if 'clip_id' in df.columns else None,
            'evaluation_scope': 'held-out test CSV; verify subject IDs were excluded from training',
        },
        'test_set_evaluation': test_results,
        'model_info': {
            'model_path': model_path,
            'model_type': 'Random Forest',
            'evaluation_date': pd.Timestamp.now().isoformat(),
        },
    }

    evaluator.save_evaluation_results(final_results, Path(output_json))

    print("\n" + "=" * 60)
    print("FALL DETECTION EVALUATION RESULTS")
    print("=" * 60)
    print(f"Held-out samples: {len(df)} from {df['subject_id'].nunique()} subjects")
    print(f"Precision: {test_results['precision']:.3f}")
    print(f"Recall:    {test_results['recall']:.3f}")
    print(f"F1-Score:  {test_results['f1']:.3f}")
    if test_results['roc_auc'] is not None:
        print(f"ROC AUC:   {test_results['roc_auc']:.3f}")
    print(f"Results saved to: {output_json}")
    print("=" * 60)
    return final_results

if __name__ == "__main__":
    # Example usage
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python evaluate.py <features_csv> [model_path] [output_json]")
        sys.exit(1)
    
    features_csv = sys.argv[1]
    model_path = sys.argv[2] if len(sys.argv) > 2 else "models/rf_baseline.joblib"
    output_json = sys.argv[3] if len(sys.argv) > 3 else "report/evaluation_results.json"
    
    try:
        results = evaluate_fall_detection(features_csv, model_path, config_path="config.yaml", output_json=output_json)
        print("\nEvaluation completed successfully!")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        print(f"Evaluation failed: {e}")
        sys.exit(1)
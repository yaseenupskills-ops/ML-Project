"""
Random Forest Baseline Model
---------------------------
Trains and evaluates a Random Forest classifier for fall detection.
Uses subject-independent splitting to prevent data leakage.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
import joblib
import logging

from project_config import load_config
from typing import Tuple, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_SCHEMA_VERSION = 1


class FallDetectionRF:
    """Random Forest classifier for fall detection with subject-independent evaluation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        self.config = load_config(config_path)
        
        # Model parameters
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',  # Handle class imbalance
            random_state=42,
            n_jobs=-1
        )
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = None
        self.artifact_metadata: Dict[str, Any] = {}
        
        logger.info("FallDetectionRF initialized")
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare features and labels from DataFrame.
        
        Args:
            df: DataFrame with features, subject_id, clip_id, and label columns
            
        Returns:
            Tuple of (X, y, groups) where groups is subject_id for GroupKFold
        """
        # Identify feature columns (exclude metadata)
        meta_cols = ['subject_id', 'clip_id', 'window_start', 'window_end', 
                    'window_start_time', 'window_end_time']
        label_cols = ['label', 'fall', 'activity']  # Possible label column names
        
        # Find label column
        label_col = None
        for col in label_cols:
            if col in df.columns:
                label_col = col
                break
        
        if label_col is None:
            raise ValueError(f"No label column found. Available: {list(df.columns)}")
        
        # Feature columns are everything except metadata and label. Once a
        # model has been loaded, preserve its training order and reject schema
        # drift instead of silently feeding columns in a different order.
        candidate_cols = [col for col in df.columns
                          if col not in meta_cols + [label_col]]
        if len(candidate_cols) == 0:
            raise ValueError("No feature columns found")

        if self.feature_names is not None:
            expected = list(self.feature_names)
            missing = [name for name in expected if name not in candidate_cols]
            extra = [name for name in candidate_cols if name not in expected]
            if missing or extra:
                raise ValueError(
                    "Feature schema does not match the trained model; "
                    f"missing={missing}, unexpected={extra}"
                )
            feature_cols = expected
        else:
            feature_cols = candidate_cols
            self.feature_names = feature_cols

        X = df[feature_cols].values
        y = df[label_col].values
        if not set(pd.unique(y)).issubset({0, 1, 0.0, 1.0}):
            raise ValueError("Labels must be binary values encoded as 0/1")
        y = y.astype(int)
        groups = df['subject_id'].values

        # Handle missing values
        if np.any(np.isnan(X)):
            logger.warning("Found NaN values in features - filling with 0")
            X = np.nan_to_num(X, nan=0.0)

        logger.info(f"Prepared {X.shape[0]} samples with {X.shape[1]} features")
        logger.info(f"Label distribution: {np.bincount(y.astype(int))}")
        logger.info(f"Unique subjects: {np.unique(groups)}")

        return X, y, groups
    
    def train(self, X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> Dict[str, float]:
        """
        Train the Random Forest with subject-independent cross-validation.
        
        Args:
            X: Feature matrix
            y: Label vector
            groups: Subject IDs for GroupKFold
            
        Returns:
            Dictionary of cross-validation metrics
        """
        logger.info("Starting subject-independent cross-validation training")
        
        # Use GroupKFold to prevent leakage, but fail clearly when the data
        # does not contain enough independent subjects.
        n_subjects = len(np.unique(groups))
        if n_subjects < 2:
            raise ValueError(
                "Subject-independent training requires at least two subject IDs; "
                f"received {n_subjects}."
            )
        n_splits = min(5, n_subjects)
        group_kfold = GroupKFold(n_splits=n_splits)
        
        cv_scores = []
        cv_reports = []
        
        for fold, (train_idx, test_idx) in enumerate(group_kfold.split(X, y, groups)):
            logger.info(f"Processing fold {fold+1}/{n_splits}")
            
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Scale features (fit on train only)
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Predict and evaluate
            y_pred = self.model.predict(X_test_scaled)
            
            # Compute metrics
            f1 = f1_score(y_test, y_pred, average='binary', zero_division=0)
            precision = precision_score(y_test, y_pred, average='binary', zero_division=0)
            recall = recall_score(y_test, y_pred, average='binary', zero_division=0)
            
            cv_scores.append({
                'fold': fold,
                'f1': f1,
                'precision': precision,
                'recall': recall
            })
            
            # Store detailed report for first fold
            if fold == 0:
                report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
                cv_reports.append(report)
                
                cm = confusion_matrix(y_test, y_pred)
                logger.info(f"Fold {fold+1} Confusion Matrix:\n{cm}")
        
        # Aggregate CV results
        cv_f1_scores = [score['f1'] for score in cv_scores]
        cv_precision_scores = [score['precision'] for score in cv_scores]
        cv_recall_scores = [score['recall'] for score in cv_scores]
        
        cv_results = {
            'cv_f1_mean': np.mean(cv_f1_scores),
            'cv_f1_std': np.std(cv_f1_scores),
            'cv_precision_mean': np.mean(cv_precision_scores),
            'cv_precision_std': np.std(cv_precision_scores),
            'cv_recall_mean': np.mean(cv_recall_scores),
            'cv_recall_std': np.std(cv_recall_scores),
            'cv_f1_scores': cv_f1_scores,
            'cv_precision_scores': cv_precision_scores,
            'cv_recall_scores': cv_recall_scores
        }
        
        # Final training on full dataset
        logger.info("Training final model on full dataset")
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        
        logger.info(f"Training complete. CV F1: {cv_results['cv_f1_mean']:.3f} ± {cv_results['cv_f1_std']:.3f}")
        
        return cv_results
    
    def _transform_for_predict(self, X: np.ndarray) -> np.ndarray:
        """Validate and scale a raw feature matrix exactly once."""
        if not self.is_fitted:
            raise RuntimeError("Model must be trained or loaded before prediction")
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"Expected a 2D feature matrix, got shape {X.shape}")
        if self.feature_names is not None and X.shape[1] != len(self.feature_names):
            raise ValueError(
                f"Expected {len(self.feature_names)} features, got {X.shape[1]}"
            )
        if np.any(~np.isfinite(X)):
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        return self.scaler.transform(X)

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict labels and probabilities from **raw** features.

        Callers should not scale ``X`` before calling this method; the fitted
        scaler is applied internally exactly once.
        """
        X_scaled = self._transform_for_predict(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)[:, 1]
        return predictions, probabilities

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities from raw features."""
        X_scaled = self._transform_for_predict(X)
        return self.model.predict_proba(X_scaled)
    
    def get_feature_importance(self) -> Optional[np.ndarray]:
        """Get feature importances from trained model."""
        if not self.is_fitted:
            return None
        return self.model.feature_importances_
    
    def save_model(self, filepath: Path):
        """Save trained model and scaler."""
        filepath = Path(filepath)
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_fitted': self.is_fitted,
            'feature_schema_version': MODEL_SCHEMA_VERSION,
            'feature_config': {
                'window_sec': self.config.get('features', {}).get('window_sec'),
                'fps': self.config.get('features', {}).get('fps'),
                'frame_stride': self.config.get('pose', {}).get('frame_stride', 1),
            },
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: Path):
        """Load trained model and scaler."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        model_data = joblib.load(filepath)
        if not isinstance(model_data, dict) or 'model' not in model_data or 'scaler' not in model_data:
            raise ValueError(f"Unsupported model artifact format: {filepath}")
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data.get('feature_names')
        self.artifact_metadata = {
            'feature_schema_version': model_data.get('feature_schema_version', 0),
            'feature_config': model_data.get('feature_config', {}),
        }
        fitted_value = model_data.get('is_fitted', True)
        self.is_fitted = True if fitted_value is None else bool(fitted_value)
        schema_version = model_data.get('feature_schema_version', 0)
        if schema_version != MODEL_SCHEMA_VERSION:
            logger.warning(
                "Model artifact uses feature schema version %s; runtime expects %s",
                schema_version, MODEL_SCHEMA_VERSION,
            )
        if self.feature_names is not None and hasattr(self.scaler, 'n_features_in_'):
            if len(self.feature_names) != int(self.scaler.n_features_in_):
                raise ValueError("Model feature names do not match scaler dimensions")

        logger.info(f"Model loaded from {filepath}")

def train_rf_model(features_csv: str, 
                  model_output: str = "models/rf_baseline.joblib",
                  config_path: str = "config.yaml") -> Dict[str, float]:
    """
    Convenience function to train RF model from features CSV.
    
    Args:
        features_csv: Path to features CSV file
        model_output: Path to save trained model
        config_path: Path to configuration file
        
    Returns:
        Dictionary of cross-validation results
    """
    # Load features
    df = pd.read_csv(features_csv)
    logger.info(f"Loaded features from {features_csv}: {len(df)} rows")
    
    # Initialize and train model
    rf_model = FallDetectionRF(config_path)
    cv_results = rf_model.train(*rf_model.prepare_features(df))
    
    # Save model
    rf_model.save_model(Path(model_output))
    
    return cv_results

def evaluate_rf_model(features_csv: str,
                     model_path: str = "models/rf_baseline.joblib",
                     config_path: str = "config.yaml") -> Dict[str, float]:
    """
    Convenience function to evaluate RF model on test set.
    
    Args:
        features_csv: Path to features CSV file (test set)
        model_path: Path to trained model
        config_path: Path to configuration file
        
    Returns:
        Dictionary of evaluation metrics
    """
    # Load test features
    df = pd.read_csv(features_csv)
    logger.info(f"Loaded test features from {features_csv}: {len(df)} rows")
    
    # Load model
    rf_model = FallDetectionRF(config_path)
    rf_model.load_model(Path(model_path))
    
    # Prepare data
    X, y, groups = rf_model.prepare_features(df)
    
    # Predict
    y_pred, y_proba = rf_model.predict(X)
    
    # Compute metrics
    metrics = {
        'accuracy': np.mean(y_pred == y),
        'precision': precision_score(y, y_pred, average='binary', zero_division=0),
        'recall': recall_score(y, y_pred, average='binary', zero_division=0),
        'f1': f1_score(y, y_pred, average='binary', zero_division=0),
        'roc_auc': None  # Would need probabilities for full ROC
    }
    
    # Per-class metrics
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)
    metrics['per_class'] = report
    
    # Confusion matrix
    cm = confusion_matrix(y, y_pred)
    metrics['confusion_matrix'] = cm.tolist()
    
    logger.info(f"Evaluation results: {metrics}")
    
    return metrics

if __name__ == "__main__":
    # Example usage
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        features_csv = sys.argv[1]
        
        if len(sys.argv) > 2:
            # Training mode
            model_output = sys.argv[2] if len(sys.argv) > 2 else "models/rf_baseline.joblib"
            print(f"Training RF model from {features_csv}")
            results = train_rf_model(features_csv, model_output)
            print(f"CV Results: F1 = {results['cv_f1_mean']:.3f} ± {results['cv_f1_std']:.3f}")
        else:
            # Evaluation mode
            print(f"Evaluating RF model on {features_csv}")
            results = evaluate_rf_model(features_csv)
            print(f"Results: {results}")
    else:
        print("Usage:")
        print("  Training:  python model_rf.py <features_csv> [model_output]")
        print("  Evaluation: python model_rf.py <features_csv>")
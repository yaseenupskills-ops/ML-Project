"""
CNN-LSTM Model for Fall Detection (Stretch Goal)
-----------------------------------------------
Implements a 1D-CNN + LSTM architecture for temporal fall detection.
This is a stretch goal - the Random Forest baseline is the primary deliverable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import yaml
import logging
from pathlib import Path
from typing import Tuple, Optional
import joblib

logger = logging.getLogger(__name__)

class FallDetectionDataset(Dataset):
    """PyTorch Dataset for fall detection sequences."""
    
    def __init__(self, X: np.ndarray, y: np.ndarray):
        """
        Args:
            X: Feature sequences of shape (n_samples, seq_len, n_features)
            y: Labels of shape (n_samples,)
        """
        self.X = torch.FloatTensor(X)
        self.y = torch.LongTensor(y)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class FallCNNLSTM(nn.Module):
    """
    1D-CNN + LSTM for fall detection from keypoint sequences.
    
    Architecture:
    - Input: (batch, seq_len, n_features) - normalized keypoint sequences
    - CNN: Extracts local temporal patterns
    - LSTM: Captures long-term dependencies (impact → stillness)
    - Output: Classification (fall vs non-fall)
    """
    
    def __init__(self, 
                 n_features: int,
                 seq_len: int,
                 n_classes: int = 2,
                 cnn_channels: Tuple[int, int] = (64, 128),
                 lstm_hidden: int = 128,
                 lstm_layers: int = 2,
                 dropout: float = 0.5):
        """
        Args:
            n_features: Number of input features per timestep
            seq_len: Length of input sequence
            n_classes: Number of output classes (2 for binary fall/no-fall)
            cnn_channels: Tuple of output channels for CNN layers
            lstm_hidden: Hidden size for LSTM layers
            lstm_layers: Number of LSTM layers
            dropout: Dropout rate
        """
        super(FallCNNLSTM, self).__init__()
        
        self.seq_len = seq_len
        self.n_features = n_features
        
        # CNN layers for local feature extraction
        self.conv1 = nn.Conv1d(n_features, cnn_channels[0], kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(cnn_channels[0], cnn_channels[1], kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        
        # LSTM for temporal modeling
        self.lstm = nn.LSTM(
            input_size=cnn_channels[1],
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0
        )
        
        # Fully connected layers for classification
        self.fc1 = nn.Linear(lstm_hidden, lstm_hidden // 2)
        self.fc2 = nn.Linear(lstm_hidden // 2, n_classes)
        
        logger.info(f"FallCNNLSTM initialized: "
                   f"input=({seq_len}, {n_features}), "
                   f"CNN={list(cnn_channels)}, "
                   f"LSTM={lstm_layers}x{lstm_hidden}, "
                   f"classes={n_classes}")
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (batch, seq_len, n_features)
            
        Returns:
            Output logits of shape (batch, n_classes)
        """
        # CNN expects (batch, channels, seq_len)
        x = x.transpose(1, 2)  # (batch, n_features, seq_len)
        
        # CNN layers
        x = self.dropout(self.relu(self.conv1(x)))
        x = self.dropout(self.relu(self.conv2(x)))
        
        # Back to (batch, seq_len, channels) for LSTM
        x = x.transpose(1, 2)  # (batch, seq_len, cnn_channels[1])
        
        # LSTM layers
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Use last time step output for classification
        # Alternative: use attention or mean pooling
        last_output = lstm_out[:, -1, :]  # (batch, lstm_hidden)
        
        # Fully connected layers
        x = self.dropout(self.relu(self.fc1(last_output)))
        output = self.fc2(x)
        
        return output

class FallDetectionCNNLSTM:
    """Wrapper for CNN-LSTM fall detection model."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        self.model = None
        self.seq_len = None
        self.n_features = None
        self.class_names = ['no_fall', 'fall']
        
    def prepare_sequences(self, 
                         features_df: pd.DataFrame,
                         window_size_sec: float = 3.0,
                         fps: float = 30.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert feature DataFrame to sequences for CNN-LSTM.
        
        Args:
            features_df: DataFrame with features and labels
            window_size_sec: Duration of each sequence in seconds
            fps: Frames per second (used to calculate seq_len)
            
        Returns:
            Tuple of (X_sequences, y_labels)
        """
        # This is a simplified implementation
        # In practice, you'd need to group by subject/clip and create sequences
        # For now, we'll use individual windows as sequences of length 1
        # A proper implementation would create overlapping sequences of multiple windows
        
        logger.warning("Using simplified sequence preparation - each window is a sequence of length 1")
        
        # Identify feature columns
        meta_cols = ['subject_id', 'clip_id', 'window_start', 'window_end', 
                    'window_start_time', 'window_end_time']
        label_cols = ['label', 'fall', 'activity']
        
        label_col = None
        for col in label_cols:
            if col in features_df.columns:
                label_col = col
                break
        
        if label_col is None:
            raise ValueError(f"No label column found in DataFrame")
        
        feature_cols = [col for col in features_df.columns 
                       if col not in meta_cols + [label_col]]
        
        X = features_df[feature_cols].values
        y = features_df[label_col].values
        
        # For sequence length of 1, reshape to (n_samples, 1, n_features)
        X_seq = X.reshape((X.shape[0], 1, X.shape[1]))
        
        self.seq_len = 1
        self.n_features = X.shape[1]
        
        return X_seq, y
    
    def build_model(self, n_features: int, seq_len: int, n_classes: int = 2):
        """Build the CNN-LSTM model."""
        self.model = FallCNNLSTM(
            n_features=n_features,
            seq_len=seq_len,
            n_classes=n_classes,
            cnn_channels=(64, 128),
            lstm_hidden=128,
            lstm_layers=2,
            dropout=0.5
        ).to(self.device)
        
        logger.info(f"CNN-LSTM model built and moved to {self.device}")
    
    def train(self, 
             X_train: np.ndarray, 
             y_train: np.ndarray,
             X_val: Optional[np.ndarray] = None,
             y_val: Optional[np.ndarray] = None,
             epochs: int = 50,
             batch_size: int = 32,
             learning_rate: float = 0.001,
             early_stopping_patience: int = 10) -> dict:
        """
        Train the CNN-LSTM model.
        
        Args:
            X_train: Training sequences (n_samples, seq_len, n_features)
            y_train: Training labels
            X_val: Validation sequences (optional)
            y_val: Validation labels (optional)
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate for Adam optimizer
            early_stopping_patience: Patience for early stopping
            
        Returns:
            Dictionary with training history
        """
        if self.model is None:
            # Build model if not already built
            self.build_model(X_train.shape[2], X_train.shape[1])
        
        # Create datasets and data loaders
        train_dataset = FallDetectionDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        if X_val is not None and y_val is not None:
            val_dataset = FallDetectionDataset(X_val, y_val)
            val_loader = DataLoader(val_dataset, batch_size=batch_size)
        else:
            val_loader = None
        
        # Loss function and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5, verbose=True)
        
        # Training history
        history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': []
        }
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        logger.info(f"Starting training for {epochs} epochs")
        
        for epoch in range(epochs):
            # Training phase
            self.model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                # Zero gradients
                optimizer.zero_grad()
                
                # Forward pass
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                
                # Backward pass and optimize
                loss.backward()
                optimizer.step()
                
                # Statistics
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_total += batch_y.size(0)
                train_correct += (predicted == batch_y).sum().item()
            
            avg_train_loss = train_loss / len(train_loader)
            train_acc = 100 * train_correct / train_total
            
            # Validation phase
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            if val_loader is not None:
                self.model.eval()
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        batch_X = batch_X.to(self.device)
                        batch_y = batch_y.to(self.device)
                        
                        outputs = self.model(batch_X)
                        loss = criterion(outputs, batch_y)
                        
                        val_loss += loss.item()
                        _, predicted = torch.max(outputs.data, 1)
                        val_total += batch_y.size(0)
                        val_correct += (predicted == batch_y).sum().item()
                
                avg_val_loss = val_loss / len(val_loader)
                val_acc = 100 * val_correct / val_total
                scheduler.step(avg_val_loss)
                
                # Early stopping check
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    
                if patience_counter >= early_stopping_patience:
                    logger.info(f"Early stopping triggered at epoch {epoch+1}")
                    break
            else:
                avg_val_loss = 0.0
                val_acc = 0.0
            
            # Record history
            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(avg_val_loss)
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            
            # Log progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(f'Epoch [{epoch+1}/{epochs}], '
                           f'Train Loss: {avg_train_loss:.4f}, Train Acc: {train_acc:.2f}%, '
                           f'Val Loss: {avg_val_loss:.4f}, Val Acc: {val_acc:.2f}%')
        
        logger.info("Training completed")
        return history
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.
        
        Args:
            X: Input sequences (n_samples, seq_len, n_features)
            
        Returns:
            Probabilities of shape (n_samples, n_classes)
        """
        if self.model is None:
            raise RuntimeError("Model must be built or loaded before prediction")
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            outputs = self.model(X_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            return probabilities.cpu().numpy()
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class labels.
        
        Args:
            X: Input sequences (n_samples, seq_len, n_features)
            
        Returns:
            Predictions of shape (n_samples,)
        """
        probabilities = self.predict_proba(X)
        return np.argmax(probabilities, axis=1)
    
    def save_model(self, filepath: Path):
        """Save the trained model."""
        if self.model is None:
            logger.warning("No model to save")
            return
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        model_data = {
            'model_state_dict': self.model.state_dict(),
            'seq_len': self.seq_len,
            'n_features': self.n_features,
            'class_names': self.class_names,
            'model_architecture': 'FallCNNLSTM'
        }
        torch.save(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: Path):
        """Load a trained model."""
        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        model_data = torch.load(
            filepath, map_location=self.device, weights_only=True
        )
        
        # Rebuild model
        self.seq_len = model_data['seq_len']
        self.n_features = model_data['n_features']
        self.class_names = model_data['class_names']
        
        self.build_model(self.n_features, self.seq_len)
        self.model.load_state_dict(model_data['model_state_dict'])
        self.model.to(self.device)
        
        logger.info(f"Model loaded from {filepath}")

# Convenience functions
def build_cnn_lstm_model(n_features: int, seq_len: int) -> FallCNNLSTM:
    """Build a CNN-LSTM model with default parameters."""
    return FallCNNLSTM(
        n_features=n_features,
        seq_len=seq_len,
        n_classes=2,
        cnn_channels=(64, 128),
        lstm_hidden=128,
        lstm_layers=2,
        dropout=0.5
    )

def train_cnn_lstm_model(features_csv: str,
                        model_output: str = "models/cnn_lstm.pt",
                        config_path: str = "config.yaml") -> dict:
    """
    Convenience function to train CNN-LSTM model.
    
    Note: This is a stretch goal implementation.
    """
    logger.warning("CNN-LSTM training is a stretch goal. Using simplified implementation.")
    
    # Load features
    df = pd.read_csv(features_csv)
    
    # Initialize model handler
    cnn_lstm_model = FallDetectionCNNLSTM(config_path)
    
    # Prepare sequences (simplified)
    X, y = cnn_lstm_model.prepare_sequences(df)
    
    # Build and train model
    cnn_lstm_model.build_model(X.shape[2], X.shape[1])
    
    # Simple train/test split (80/20)
    split_idx = int(0.8 * len(X))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Train model
    history = cnn_lstm_model.train(
        X_train, y_train,
        X_val=X_test, y_val=y_test,
        epochs=30,  # Reduced for stretch goal
        batch_size=32
    )
    
    # Save model
    cnn_lstm_model.save_model(Path(model_output))
    
    return {
        'history': history,
        'model_path': str(model_output),
        'n_features': X.shape[2],
        'seq_len': X.shape[1]
    }

if __name__ == "__main__":
    # Example usage
    import sys
    import pandas as pd
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python model_cnn_lstm.py <features_csv> [model_output]")
        print("Note: This is a stretch goal implementation")
        sys.exit(1)
    
    features_csv = sys.argv[1]
    model_output = sys.argv[2] if len(sys.argv) > 2 else "models/cnn_lstm.pt"
    
    print("Training CNN-LSTM model (stretch goal)...")
    try:
        result = train_cnn_lstm_model(features_csv, model_output)
        print(f"Training completed. Model saved to {result['model_path']}")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        print(f"Training failed: {e}")
        sys.exit(1)
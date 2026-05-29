#!/usr/bin/env python3
"""
nn_agent.py — Neural Network Agent with PyTorch LSTM
=====================================================
Learns temporal patterns across 60-day indicator windows to predict
direction (5-class) and recommend position sizes. Applies user-defined
position caps via min(agent_recommended, user_cap) logic.

Pipeline position: SECOND — takes GA-optimized weights as features.
Writes to nn_predictions with both raw_weight and user_cap_weight.

Architecture:
  Input: 60-day sequence × 25 features (TA + scoring + GA weights)
  Encoder: 2-layer LSTM with dropout
  Heads:
    direction_head: 5-class classifier (STRONG_BUY → STRONG_SELL)
    confidence_head: scalar sigmoid (probability of correctness)
    weight_head: scalar (recommended position size 0-15%)
  Loss: CrossEntropy(direction) + MSE(confidence) + MSE(weight)
  Output: direction, confidence, raw_weight, user_cap_weight → nn_predictions

Usage:
  python3 nn_agent.py                                    # Train on all symbols
  python3 nn_agent.py --symbols RY.TO,TD.TO,ENB.TO      # Specific symbols
  python3 nn_agent.py --epochs 200 --hidden 256         # Larger model
  python3 nn_agent.py --predict-only                     # Inference mode
  python3 nn_agent.py --predict AAPL,MSFT               # Predict specific
"""

import argparse
import json
import logging
import math
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

# PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset, random_split
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("WARNING: PyTorch not available. Install with: pip install torch")

# Project imports
from python.db_connector import get_connection, get_active_symbols, fetch_price_data

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ===========================================================================
# CONFIGURATION
# ===========================================================================

DEFAULT_CONFIG = {
    'sequence_length': 60,
    'hidden_size': 128,
    'num_layers': 2,
    'dropout': 0.2,
    'learning_rate': 0.001,
    'batch_size': 64,
    'epochs': 100,
    'early_stopping_patience': 10,
    'train_split': 0.8,
    'confidence_threshold': 0.6,
    'max_recommended_weight': 0.15,
    'min_recommended_weight': 0.01,
    'num_direction_classes': 5,
    'seed': 42,
}

# Feature columns — 25 wide features fed to LSTM
# From daily_indicators (Tier 1) + daily_tier2 (Tier 2) + scoring evalsummary
FEATURE_COLUMNS = [
    # Price/volume (from stockprices, joined via view or query)
    'day_return', 'gap_pct',
    # Tier 1 (daily_indicators)
    'sma_20', 'sma_50', 'sma_200', 'volume_sma_20',
    'volume_ratio',  # volume / volume_sma_20
    # Tier 2 (daily_tier2)
    'bb_width', 'bb_pct', 'atr_14', 'atr_pct',
    'vol_ratio_20', 'vol_ratio_50',
    # Derived
    'price_vs_sma20',  # close / sma_20 - 1
    'price_vs_sma50',  # close / sma_50 - 1
    'price_vs_sma200', # close / sma_200 - 1
    'sma50_vs_sma200', # sma_50 / sma_200 - 1 (golden/death cross proxy)
    # Tier 3 common (from ta_values narrow table)
    'rsi_14', 'macd_hist', 'cci_14', 'adx_14', 'willr_14',
    # Scoring composite (from evalsummary, forward-filled)
    'totalscore_norm',  # totalscore / 36
    'marginsafety_norm', # marginsafety / 100
]

NUM_FEATURES = len(FEATURE_COLUMNS)

# Direction classes
DIRECTION_CLASSES = ['STRONG_SELL', 'SELL', 'HOLD', 'BUY', 'STRONG_BUY']
DIRECTION_TO_IDX = {d: i for i, d in enumerate(DIRECTION_CLASSES)}
IDX_TO_DIRECTION = {i: d for i, d in enumerate(DIRECTION_CLASSES)}


# ===========================================================================
# USER POSITION CAP ENFORCER
# ===========================================================================

class PositionCapEnforcer:
    """
    Enforces user-defined position sizing caps.
    Rule: effective_weight = min(agent_recommended, user_cap)

    Hierarchy (most specific wins):
      1. symbol cap (e.g., AAPL max 5%)
      2. sector cap (e.g., Tech max 8%)
      3. region cap (e.g., EMERGING max 5%)
      4. account cap (e.g., TFSA max 10%)
      5. global default (max 10%)
    """

    def __init__(self, conn):
        self.conn = conn
        self._cache = {}
        self._load_caps()

    def _load_caps(self):
        """Load all active caps from the database."""
        from python.db_connector import get_dict_cursor
        cursor = get_dict_cursor(self.conn)
        cursor.execute("""
            SELECT cap_type, cap_target, max_position_pct
            FROM user_position_caps
            WHERE is_active = 1
            ORDER BY cap_type, cap_target
        """)
        self._caps = {}
        for row in cursor.fetchall():
            ctype = row['cap_type']
            target = row['cap_target']
            pct = float(row['max_position_pct'])
            if ctype not in self._caps:
                self._caps[ctype] = {}
            self._caps[ctype][target] = pct
        cursor.close()
        logger.debug(f"Loaded position caps: {json.dumps(self._caps, indent=2)}")

    def get_symbol_region(self, symbol: str) -> str:
        """Determine region for a symbol based on suffix/prefix."""
        if symbol.endswith('.TO') or symbol.endswith('.CN'):
            return 'CDN'
        elif symbol.endswith('.L') or symbol.endswith('.PA') or \
             symbol.endswith('.DE') or symbol.endswith('.AS') or \
             symbol.endswith('.MI') or symbol.endswith('.BR') or \
             symbol.endswith('.SW'):
            return 'EURO'
        elif symbol.endswith('.SI') or symbol.endswith('.HK') or \
             symbol.endswith('.T') or symbol.endswith('.BO') or \
             symbol.endswith('.NS') or symbol.endswith('.SS'):
            return 'EMERGING'
        else:
            # NYSE/NASDAQ/CBOE/TSX → USA
            return 'USA'

    def get_effective_weight(self, agent_weight: float, symbol: str = None,
                              account: str = 'RRSP') -> Tuple[float, str]:
        """
        Apply the tightest cap to the agent's recommended weight.
        Returns (effective_weight, reason).
        """
        caps_applied = []

        # Start with agent's recommendation
        effective = agent_weight
        reason = 'agent_recommended'

        # Symbol-specific cap
        if symbol and 'symbol' in self._caps and symbol in self._caps['symbol']:
            cap = self._caps['symbol'][symbol]
            if cap < effective:
                effective = cap
                reason = f'symbol_cap({symbol})={cap:.1%}'
            caps_applied.append(f'symbol={cap:.1%}')

        # Region cap
        if symbol:
            region = self.get_symbol_region(symbol)
            if 'region' in self._caps and region in self._caps['region']:
                cap = self._caps['region'][region]
                if cap < effective:
                    effective = cap
                    reason = f'region_cap({region})={cap:.1%}'
                caps_applied.append(f'region={cap:.1%}')

        # Account cap
        if 'account' in self._caps and account in self._caps['account']:
            cap = self._caps['account'][account]
            if cap < effective:
                effective = cap
                reason = f'account_cap({account})={cap:.1%}'
            caps_applied.append(f'account={cap:.1%}')

        # Global default
        if 'global' in self._caps and 'default' in self._caps['global']:
            cap = self._caps['global']['default']
            if cap < effective:
                effective = cap
                reason = f'global_cap={cap:.1%}'
            caps_applied.append(f'global={cap:.1%}')

        # Clamp to [min_recommended, 1.0]
        effective = max(DEFAULT_CONFIG['min_recommended_weight'], min(effective, 1.0))

        if effective < agent_weight:
            logger.debug(
                f"  Cap applied: {symbol} agent={agent_weight:.3f} → "
                f"effective={effective:.3f} ({reason})"
            )

        return effective, reason


# ===========================================================================
# DATA LOADING & FEATURE ENGINEERING
# ===========================================================================

def fetch_feature_matrix(conn, symbol: str, as_of_date: date,
                          sequence_length: int = 60):
    """
    Fetch and engineer features for a single symbol.
    Returns (features_array, targets_array, dates_array) or None.

    features_array shape: (num_sequences, sequence_length, num_features)
    targets_array shape: (num_sequences,) — direction class index
    """
    cursor = conn.cursor(dictionary=True)

    # Get extended history for lookback
    lookback_days = sequence_length + 250  # Extra for training sequences
    start_date = as_of_date - timedelta(days=lookback_days * 2)  # Calendar days

    # Fetch joined price + indicators data
    cursor.execute("""
        SELECT
            sp.price_date,
            sp.day_open, sp.day_high, sp.day_low, sp.day_close, sp.volume,
            di.daily_return, di.gap_pct, di.sma_20, di.sma_50, di.sma_200,
            di.volume_sma_20,
            dt.bb_width, dt.bb_pct, dt.atr_14, dt.atr_pct,
            dt.vol_ratio_20, dt.vol_ratio_50,
            es.totalscore, es.marginsafety
        FROM stockprices sp
        LEFT JOIN daily_indicators di
            ON sp.symbol = di.symbol AND sp.price_date = di.price_date
        LEFT JOIN daily_tier2 dt
            ON sp.symbol = dt.symbol AND sp.price_date = dt.price_date
        LEFT JOIN evalsummary es
            ON sp.symbol = es.symbol
        WHERE sp.symbol = %s
          AND sp.price_date BETWEEN %s AND %s
        ORDER BY sp.price_date ASC
    """, (symbol, start_date, as_of_date))

    rows = cursor.fetchall()
    cursor.close()

    if len(rows) < sequence_length + 20:
        logger.debug(f"[{symbol}] Insufficient data: {len(rows)} rows")
        return None

    # Build feature matrix
    data = []
    dates = []
    for i, row in enumerate(rows):
        close = float(row['day_close']) if row['day_close'] else None
        sma20 = float(row['sma_20']) if row['sma_20'] else None
        sma50 = float(row['sma_50']) if row['sma_50'] else None
        sma200 = float(row['sma_200']) if row['sma_200'] else None
        vol = float(row['volume']) if row['volume'] else None
        vol_sma20 = float(row['volume_sma_20']) if row['volume_sma_20'] else None

        # Skip rows with null close
        if close is None or close <= 0:
            continue

        # Volume ratio
        vol_ratio = vol / vol_sma20 if vol and vol_sma20 and vol_sma20 > 0 else 1.0

        # Price vs SMAs
        p_vs_sma20 = close / sma20 - 1 if sma20 and sma20 > 0 else 0.0
        p_vs_sma50 = close / sma50 - 1 if sma50 and sma50 > 0 else 0.0
        p_vs_sma200 = close / sma200 - 1 if sma200 and sma200 > 0 else 0.0
        sma50_vs_200 = sma50 / sma200 - 1 if sma50 and sma200 and sma200 > 0 else 0.0

        # Features in FEATURE_COLUMNS order
        features = [
            float(row['daily_return'] or 0),       # day_return
            float(row['gap_pct'] or 0),            # gap_pct
            sma20 or close,                         # sma_20 (fallback to close)
            sma50 or close,                         # sma_50
            sma200 or close,                        # sma_200
            vol_sma20 or (vol or 0),               # volume_sma_20
            vol_ratio,                              # volume_ratio
            float(row['bb_width'] or 0),           # bb_width
            float(row['bb_pct'] or 0.5),           # bb_pct
            float(row['atr_14'] or 0),             # atr_14
            float(row['atr_pct'] or 0),            # atr_pct
            float(row['vol_ratio_20'] or 1.0),    # vol_ratio_20
            float(row['vol_ratio_50'] or 1.0),    # vol_ratio_50
            p_vs_sma20,                             # price_vs_sma20
            p_vs_sma50,                             # price_vs_sma50
            p_vs_sma200,                            # price_vs_sma200
            sma50_vs_200,                           # sma50_vs_sma200
            # Tier 3 proxy features (use what's available from filled indicators)
            50.0,  # rsi_14 — neutral default
            0.0,   # macd_hist — neutral
            0.0,   # cci_14 — neutral
            25.0,  # adx_14 — neutral
            -50.0, # willr_14 — neutral
            # Scoring (normalized)
            float(row['totalscore'] or 18) / 36.0, # totalscore_norm
            float(row['marginsafety'] or 0) / 100,  # marginsafety_norm
        ]

        # Normalize features
        features = _normalize_features(features)

        data.append(features)
        dates.append(row['price_date'])

    if len(data) < sequence_length + 5:
        return None

    # Compute targets: future 5-day return → direction class
    targets = []
    valid_indices = []
    for i in range(len(data)):
        if i + 5 < len(data):
            # Use the close price ratio as target
            future_close_idx = i + 5
            # We need to store closes to compute returns
            valid_indices.append(i)

    # Build sequences
    X = []
    y = []
    target_dates = []
    closes = [float(r['day_close']) for r in rows]

    for i in range(sequence_length, len(data) - 5):
        seq = data[i - sequence_length:i]
        # Target: 5-day forward return class
        ret_5d = (closes[i + 5] - closes[i]) / closes[i] if closes[i] > 0 else 0

        # Map return to class
        if ret_5d > 0.05:
            direction_idx = 4  # STRONG_BUY
        elif ret_5d > 0.02:
            direction_idx = 3  # BUY
        elif ret_5d > -0.02:
            direction_idx = 2  # HOLD
        elif ret_5d > -0.05:
            direction_idx = 1  # SELL
        else:
            direction_idx = 0  # STRONG_SELL

        X.append(seq)
        y.append(direction_idx)
        target_dates.append(dates[i])

    if not X:
        return None

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64), target_dates


def _normalize_features(features: list) -> list:
    """Apply per-feature normalization. Uses approximate ranges."""
    # Approximate max absolute values for each feature
    scales = [
        0.15, 0.15,       # day_return, gap_pct (max ~15%)
        1.0, 1.0, 1.0,    # sma_20, sma_50, sma_200 (will be normalized via zscore later)
        1e9,               # volume_sma_20 (will use log)
        5.0,               # volume_ratio
        0.5, 1.0,          # bb_width, bb_pct
        50.0, 0.1,         # atr_14, atr_pct
        5.0, 5.0,          # vol_ratio_20, vol_ratio_50
        0.5, 0.5, 0.5,     # price vs SMAs
        0.3,               # sma50_vs_sma200
        100.0, 10.0, 500.0, 100.0, 100.0,  # RSI, MACD, CCI, ADX, WILLR
        1.0, 1.0,          # normalized scores
    ]

    normalized = []
    for i, val in enumerate(features):
        if i < len(scales):
            if scales[i] > 0:
                normalized.append(val / scales[i])
            else:
                normalized.append(0.0)
        else:
            normalized.append(val)
    return normalized


def fetch_training_data(conn, symbols: List[str], config: dict):
    """
    Fetch training data for all symbols.
    Returns (X_train, y_train, X_val, y_val, symbol_map).
    """
    all_X = []
    all_y = []
    all_dates = []
    all_symbols = []

    max_samples_per_symbol = 500  # Cap to prevent any single symbol from dominating

    for symbol in symbols:
        result = fetch_feature_matrix(
            conn, symbol,
            as_of_date=date.today(),
            sequence_length=config['sequence_length']
        )
        if result is None:
            continue

        X, y, dates = result

        # Cap samples
        if len(X) > max_samples_per_symbol:
            # Take the most recent samples
            X = X[-max_samples_per_symbol:]
            y = y[-max_samples_per_symbol:]
            dates = dates[-max_samples_per_symbol:]

        all_X.append(X)
        all_y.append(y)
        all_dates.extend(dates)
        all_symbols.extend([symbol] * len(X))

    if not all_X:
        return None

    X_all = np.concatenate(all_X, axis=0)
    y_all = np.concatenate(all_y, axis=0)

    logger.info(f"Training data: {X_all.shape[0]} sequences, "
                f"{X_all.shape[2]} features, {X_all.shape[1]} timesteps")

    # Z-score normalization per feature (using training stats)
    # Reshape to (samples * timesteps, features) for global stats
    n_samples, n_timesteps, n_features = X_all.shape
    flat = X_all.reshape(-1, n_features)
    means = flat.mean(axis=0)
    stds = flat.std(axis=0) + 1e-8  # Avoid division by zero
    X_all = ((X_all - means) / stds).astype(np.float32)

    # Train/val split
    n_total = len(X_all)
    n_train = int(n_total * config['train_split'])

    # Random shuffle but keep it reproducible
    rng = np.random.RandomState(config['seed'])
    indices = rng.permutation(n_total)
    train_idx = indices[:n_train]
    val_idx = indices[n_train:]

    X_train = X_all[train_idx]
    y_train = y_all[train_idx]
    X_val = X_all[val_idx]
    y_val = y_all[val_idx]

    logger.info(f"  Train: {X_train.shape[0]}  Val: {X_val.shape[0]}")

    return {
        'X_train': torch.FloatTensor(X_train),
        'y_train': torch.LongTensor(y_train),
        'X_val': torch.FloatTensor(X_val),
        'y_val': torch.LongTensor(y_val),
        'means': means,
        'stds': stds,
        'train_symbols': [all_symbols[i] for i in train_idx],
        'val_symbols': [all_symbols[i] for i in val_idx],
    }


# ===========================================================================
# MODEL
# ===========================================================================

class LSTMDirectionModel(nn.Module):
    """
    Multi-task LSTM:
      - direction_head: 5-class classification
      - confidence_head: scalar probability
      - weight_head: position size recommendation
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        input_size = NUM_FEATURES
        hidden = config['hidden_size']
        num_layers = config['num_layers']
        dropout = config['dropout']

        # LSTM encoder
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
        )

        # Batch norm on LSTM output
        self.bn = nn.BatchNorm1d(hidden)

        # Shared representation
        self.shared = nn.Sequential(
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Task heads
        self.direction_head = nn.Linear(hidden // 2, config['num_direction_classes'])
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden // 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        self.weight_head = nn.Sequential(
            nn.Linear(hidden // 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),  # Output 0-1, will be scaled to position size
        )

    def forward(self, x):
        """
        x shape: (batch, seq_len, num_features)
        Returns: (direction_logits, confidence, raw_weight)
        """
        # LSTM encoding — take last hidden state
        lstm_out, (h_n, c_n) = self.lstm(x)
        # h_n shape: (num_layers, batch, hidden) — take last layer
        last_hidden = h_n[-1]  # (batch, hidden)

        # Batch norm
        normed = self.bn(last_hidden)

        # Shared representation
        shared = self.shared(normed)

        # Task outputs
        direction_logits = self.direction_head(shared)  # (batch, 5)
        confidence = self.confidence_head(shared).squeeze(-1)  # (batch,)
        raw_weight = self.weight_head(shared).squeeze(-1)  # (batch,)

        return direction_logits, confidence, raw_weight


def direction_loss_fn(direction_logits, direction_targets, confidence_pred,
                      confidence_targets, weight_pred, weight_targets,
                      alpha=1.0, beta=0.5, gamma=0.3):
    """
    Combined loss:
      - alpha * CrossEntropy(direction)
      - beta * BCE(confidence, |direction_correct|)
      - gamma * MSE(weight, optimal_weight_from_returns)
    """
    ce_loss = nn.CrossEntropyLoss()(direction_logits, direction_targets)

    # Confidence target: 1.0 if top-1 prediction matches, 0.5 otherwise
    pred_classes = direction_logits.argmax(dim=1)
    correct = (pred_classes == direction_targets).float()
    bce_loss = nn.BCELoss()(confidence_pred, correct)

    # Weight loss: MSE between predicted weight and a target
    # Target weight is proportional to |confidence| * expected return
    mse_loss = nn.MSELoss()(weight_pred, weight_targets.clamp(0, 0.15))

    total = alpha * ce_loss + beta * bce_loss + gamma * mse_loss
    return total, ce_loss, bce_loss, mse_loss


# ===========================================================================
# TRAINING LOOP
# ===========================================================================

class NNTrainer:
    """Handles training and validation of the LSTM model."""

    def __init__(self, model, config, device='cpu'):
        self.model = model.to(device)
        self.config = config
        self.device = device
        self.optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, patience=5, factor=0.5, min_lr=1e-6
        )
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        self.history = {'train_loss': [], 'val_loss': [], 'val_acc': []}

    def train_epoch(self, dataloader):
        self.model.train()
        total_loss = 0
        total_ce = 0
        correct = 0
        total = 0

        for batch_X, batch_y in dataloader:
            batch_X = batch_X.to(self.device)
            batch_y = batch_y.to(self.device)

            # Forward
            direction_logits, confidence, raw_weight = self.model(batch_X)

            # Compute target weights: use return magnitude as target
            # Simple heuristic: map class to target weight
            weight_targets = torch.where(
                batch_y >= 3,  # BUY or STRONG_BUY
                torch.tensor(0.10, device=self.device),
                torch.where(
                    batch_y <= 1,  # SELL or STRONG_SELL
                    torch.tensor(0.02, device=self.device),
                    torch.tensor(0.05, device=self.device)
                )
            ).float()

            loss, ce, bce, mse = direction_loss_fn(
                direction_logits, batch_y,
                confidence, None,
                raw_weight, weight_targets
            )

            # Backward
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()

            total_loss += loss.item() * len(batch_X)
            total_ce += ce.item() * len(batch_X)

            preds = direction_logits.argmax(dim=1)
            correct += (preds == batch_y).sum().item()
            total += len(batch_X)

        return total_loss / total, correct / total

    def validate(self, dataloader):
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch_X, batch_y in dataloader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)

                direction_logits, confidence, raw_weight = self.model(batch_X)

                weight_targets = torch.where(
                    batch_y >= 3,
                    torch.tensor(0.10, device=self.device),
                    torch.where(
                        batch_y <= 1,
                        torch.tensor(0.02, device=self.device),
                        torch.tensor(0.05, device=self.device)
                    )
                ).float()

                loss, ce, bce, mse = direction_loss_fn(
                    direction_logits, batch_y,
                    confidence, None,
                    raw_weight, weight_targets
                )

                total_loss += loss.item() * len(batch_X)
                preds = direction_logits.argmax(dim=1)
                correct += (preds == batch_y).sum().item()
                total += len(batch_X)

        return total_loss / total, correct / total

    def train(self, data: dict) -> dict:
        """Full training loop with early stopping."""
        train_dataset = TensorDataset(data['X_train'], data['y_train'])
        val_dataset = TensorDataset(data['X_val'], data['y_val'])

        train_loader = DataLoader(
            train_dataset, batch_size=self.config['batch_size'], shuffle=True
        )
        val_loader = DataLoader(
            val_dataset, batch_size=self.config['batch_size'], shuffle=False
        )

        logger.info(f"Training: {len(train_dataset)} train, {len(val_dataset)} val")

        for epoch in range(self.config['epochs']):
            train_loss, train_acc = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)

            self.scheduler.step(val_loss)
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)

            # Early stopping
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                # Save best model
                self.best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
            else:
                self.patience_counter += 1

            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(
                    f"  Epoch {epoch+1}/{self.config['epochs']}: "
                    f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
                    f"val_acc={val_acc:.3f} best_val={self.best_val_loss:.4f}"
                )

            if self.patience_counter >= self.config['early_stopping_patience']:
                logger.info(f"  Early stopping at epoch {epoch+1}")
                break

        # Restore best model
        if hasattr(self, 'best_state'):
            self.model.load_state_dict(self.best_state)

        return {
            'best_val_loss': self.best_val_loss,
            'best_val_acc': max(self.history['val_acc']),
            'epochs_trained': epoch + 1,
            'history': self.history,
        }


# ===========================================================================
# NN AGENT — Main class
# ===========================================================================

class NNAgent:
    """Neural Network Agent — Trains LSTM, generates predictions, applies caps."""

    def __init__(self, conn, symbols: List[str], config: dict,
                 run_id: int = None, machine_id: str = None,
                 priority: int = 5, model_path: str = None):
        self.conn = conn
        self.symbols = symbols
        self.config = {**DEFAULT_CONFIG, **config}
        self.run_id = run_id
        self.machine_id = machine_id or os.uname().nodename
        self.priority = priority
        self.model_path = model_path or 'models/nn_lstm_latest.pt'
        self.cap_enforcer = PositionCapEnforcer(conn)
        self.norm_stats = {'means': None, 'stds': None}

        # Device
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"NN Agent using device: {self.device}")

    def _create_agent_run(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runs
                (agent_type, run_name, priority, machine_id, status,
                 symbol_target, started_at)
            VALUES ('nn', %s, %s, %s, 'running', NULL, NOW())
        """, (
            f"NN_{self.config['epochs']}ep_{len(self.symbols)}sym",
            self.priority,
            self.machine_id,
        ))
        self.conn.commit()
        run_id = cursor.lastrowid
        cursor.close()
        return run_id

    def _update_agent_run(self, status: str, result_json: dict = None,
                          error: str = None):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agent_runs
            SET status = %s,
                completed_at = NOW(),
                duration_sec = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                reward_score = %s,
                result_json = %s,
                error_message = %s
            WHERE id = %s
        """, (
            status,
            result_json.get('best_val_acc') if result_json else None,
            json.dumps(result_json) if result_json else None,
            error,
            self.run_id,
        ))
        self.conn.commit()
        cursor.close()

    def train(self) -> dict:
        """Train the LSTM model on all symbols."""
        if not HAS_TORCH:
            raise RuntimeError("PyTorch not installed. Run: pip install torch")

        if not self.run_id:
            self.run_id = self._create_agent_run()

        start_time = time.time()
        logger.info(f"NN Agent training run #{self.run_id} | "
                    f"{self.config['epochs']} epochs | {len(self.symbols)} symbols | "
                    f"seq_len={self.config['sequence_length']} | "
                    f"hidden={self.config['hidden_size']}")

        # Fetch training data
        data = fetch_training_data(self.conn, self.symbols, self.config)
        if data is None:
            raise ValueError("No training data available. Load price data and run TA calculator first.")

        # Save normalization stats
        self.norm_stats = {'means': data['means'].tolist(), 'stds': data['stds'].tolist()}

        # Create model
        model = LSTMDirectionModel(self.config)
        num_params = sum(p.numel() for p in model.parameters())
        logger.info(f"Model: {num_params:,} parameters")

        # Train
        trainer = NNTrainer(model, self.config, self.device)
        train_result = trainer.train(data)

        # Save model
        os.makedirs(os.path.dirname(self.model_path) or '.', exist_ok=True)
        torch.save({
            'model_state': model.state_dict(),
            'config': self.config,
            'norm_stats': self.norm_stats,
            'num_features': NUM_FEATURES,
            'feature_columns': FEATURE_COLUMNS,
        }, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

        elapsed = time.time() - start_time
        result = {
            'best_val_loss': train_result['best_val_loss'],
            'best_val_acc': train_result['best_val_acc'],
            'epochs_trained': train_result['epochs_trained'],
            'num_params': num_params,
            'model_path': self.model_path,
            'elapsed_sec': elapsed,
        }
        self._update_agent_run('complete', result_json=result)
        return result

    def predict(self, symbols: List[str] = None) -> List[dict]:
        """
        Generate predictions for symbols.
        Returns list of prediction dicts.
        """
        if not HAS_TORCH:
            raise RuntimeError("PyTorch not installed")

        # Load model
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"No model found at {self.model_path}. Train first.")

        checkpoint = torch.load(self.model_path, map_location='cpu')
        config = checkpoint.get('config', self.config)
        model = LSTMDirectionModel(config)
        model.load_state_dict(checkpoint['model_state'])
        model.eval()

        # Load normalization stats
        norm_stats = checkpoint.get('norm_stats', self.norm_stats)
        if norm_stats['means'] is not None:
            means = np.array(norm_stats['means'])
            stds = np.array(norm_stats['stds'])
        else:
            means = None
            stds = None

        symbols = symbols or self.symbols
        predictions = []

        for symbol in symbols:
            result = fetch_feature_matrix(
                self.conn, symbol,
                as_of_date=date.today(),
                sequence_length=config['sequence_length']
            )
            if result is None:
                continue

            X, y, dates = result
            last_date = dates[-1]

            # Get last sequence
            last_seq = X[-1:]  # (1, seq_len, features)

            # Apply normalization
            if means is not None:
                last_seq = (last_seq - means) / (stds + 1e-8)

            x_tensor = torch.FloatTensor(last_seq)

            with torch.no_grad():
                direction_logits, confidence, raw_weight = model(x_tensor)

            # Parse outputs
            probs = torch.softmax(direction_logits, dim=1)[0]
            direction_idx = probs.argmax().item()
            direction = IDX_TO_DIRECTION[direction_idx]
            conf_val = confidence[0].item()
            raw_w = raw_weight[0].item() * config['max_recommended_weight']  # Scale to max

            # Apply user caps
            effective_weight, cap_reason = self.cap_enforcer.get_effective_weight(
                raw_w, symbol=symbol
            )

            # Map direction to expected return for storage
            expected_returns = {
                'STRONG_BUY': 0.08, 'BUY': 0.04, 'HOLD': 0.0,
                'SELL': -0.04, 'STRONG_SELL': -0.08,
            }

            pred = {
                'symbol': symbol,
                'prediction_date': last_date,
                'direction': direction,
                'confidence': round(conf_val, 4),
                'raw_weight': round(raw_w, 4),
                'user_cap_weight': round(effective_weight, 4),
                'cap_reason': cap_reason,
                'predicted_return_5d': expected_returns[direction],
                'class_probs': {IDX_TO_DIRECTION[i]: round(probs[i].item(), 4)
                                for i in range(5)},
            }
            predictions.append(pred)

            # Save to database
            self._save_prediction(pred)

        logger.info(f"Generated {len(predictions)} predictions")
        return predictions

    def _save_prediction(self, pred: dict):
        """Save a single prediction to nn_predictions table."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO nn_predictions
                    (symbol, prediction_date, model_version,
                     direction, confidence,
                     predicted_return_5d, predicted_return_20d,
                     raw_weight, user_cap_weight,
                     feature_json, agent_run_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    direction = VALUES(direction),
                    confidence = VALUES(confidence),
                    predicted_return_5d = VALUES(predicted_return_5d),
                    predicted_return_20d = VALUES(predicted_return_20d),
                    raw_weight = VALUES(raw_weight),
                    user_cap_weight = VALUES(user_cap_weight),
                    agent_run_id = VALUES(agent_run_id)
            """, (
                pred['symbol'],
                pred['prediction_date'],
                f"nn_v1",
                pred['direction'],
                pred['confidence'],
                pred['predicted_return_5d'],
                pred['predicted_return_5d'] * 4,  # Rough 20d extrapolation
                pred['raw_weight'],
                pred['user_cap_weight'],
                json.dumps(pred.get('class_probs', {})),
                self.run_id,
            ))
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Failed to save prediction for {pred['symbol']}: {e}")
        finally:
            cursor.close()

    def run(self, predict_only: bool = False) -> dict:
        """Full agent run: train then predict."""
        if not self.run_id:
            self.run_id = self._create_agent_run()

        start_time = time.time()

        try:
            if not predict_only:
                # Train
                train_result = self.train()
            else:
                train_result = None

            # Predict
            predictions = self.predict()

            elapsed = time.time() - start_time
            result = {
                'training': train_result,
                'predictions_count': len(predictions),
                'predictions': predictions[:10],  # First 10 for logging
                'elapsed_sec': elapsed,
            }
            self._update_agent_run('complete', result_json=result)
            return result

        except Exception as e:
            logger.error(f"NN Agent failed: {e}")
            import traceback
            traceback.print_exc()
            self._update_agent_run('failed', error=str(e))
            raise


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='NN Agent — PyTorch LSTM for Directional Prediction'
    )
    parser.add_argument('--symbols', type=str, default='',
                        help='Comma-separated symbols (default: all active)')
    parser.add_argument('--epochs', type=int, default=DEFAULT_CONFIG['epochs'])
    parser.add_argument('--hidden', type=int, default=DEFAULT_CONFIG['hidden_size'])
    parser.add_argument('--num-layers', type=int, default=DEFAULT_CONFIG['num_layers'])
    parser.add_argument('--dropout', type=float, default=DEFAULT_CONFIG['dropout'])
    parser.add_argument('--lr', type=float, default=DEFAULT_CONFIG['learning_rate'])
    parser.add_argument('--batch-size', type=int, default=DEFAULT_CONFIG['batch_size'])
    parser.add_argument('--sequence-length', type=int, default=DEFAULT_CONFIG['sequence_length'])
    parser.add_argument('--seed', type=int, default=DEFAULT_CONFIG['seed'])
    parser.add_argument('--model-path', type=str, default='models/nn_lstm_latest.pt')
    parser.add_argument('--predict-only', action='store_true',
                        help='Only run inference (no training)')
    parser.add_argument('--predict', type=str, default=None,
                        help='Comma-separated symbols to predict (skip training)')
    parser.add_argument('--run-id', type=int, default=None)
    parser.add_argument('--machine-id', type=str, default=None)
    parser.add_argument('--priority', type=int, default=5)

    args = parser.parse_args()

    config = {
        'epochs': args.epochs,
        'hidden_size': args.hidden,
        'num_layers': args.num_layers,
        'dropout': args.dropout,
        'learning_rate': args.lr,
        'batch_size': args.batch_size,
        'sequence_length': args.sequence_length,
        'seed': args.seed,
    }

    conn = get_connection()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        symbols = get_active_symbols(conn)
        symbols = symbols[:100]  # Limit initial training

    predict_symbols = None
    if args.predict:
        predict_symbols = [s.strip().upper() for s in args.predict.split(',')]

    if not symbols and not predict_symbols:
        logger.error("No symbols available")
        sys.exit(1)

    agent = NNAgent(
        conn=conn,
        symbols=symbols or predict_symbols,
        config=config,
        run_id=args.run_id,
        machine_id=args.machine_id,
        priority=args.priority,
        model_path=args.model_path,
    )

    try:
        result = agent.run(predict_only=args.predict_only)
        if predict_symbols:
            predictions = agent.predict(predict_symbols)
            result['predictions'] = predictions

        # Print summary
        if 'predictions' in result and result['predictions']:
            print(f"\n{'='*60}")
            print(f"NN Agent Predictions Summary")
            print(f"{'='*60}")
            buys = [p for p in result['predictions'] if 'BUY' in p['direction']]
            sells = [p for p in result['predictions'] if 'SELL' in p['direction']]
            holds = [p for p in result['predictions'] if p['direction'] == 'HOLD']
            print(f"  Total: {len(result['predictions'])} | "
                  f"BUY: {len(buys)} | HOLD: {len(holds)} | SELL: {len(sells)}")
            if buys:
                buys.sort(key=lambda x: x['confidence'], reverse=True)
                print(f"\n  Top BUY signals:")
                for p in buys[:5]:
                    print(f"    {p['symbol']:8s} {p['direction']:12s} "
                          f"conf={p['confidence']:.2f} "
                          f"raw_w={p['raw_weight']:.3f} → "
                          f"capped={p['user_cap_weight']:.3f} "
                          f"({p['cap_reason']})")
            print(f"{'='*60}")

    except KeyboardInterrupt:
        logger.info("Interrupted")
        if agent.run_id:
            agent._update_agent_run('cancelled', error='KeyboardInterrupt')
    except Exception as e:
        logger.error(f"NN Agent error: {e}")
        if agent.run_id:
            agent._update_agent_run('failed', error=str(e))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()

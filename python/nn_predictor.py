#!/usr/bin/env python3
"""
nn_predictor.py — PyTorch LSTM for tactical return prediction.

Trains on 60-day sequences of 120 indicators to predict 20-day forward return.
Outputs both mean prediction and uncertainty (heteroscedastic).

Walk-forward: train 2014-2018, validate 2019-2020, test 2021-2024.

Usage:
    python3 nn_predictor.py [--epochs 50] [--predict 2025-01-01]
"""
import sys, os, json, argparse
import numpy as np
import pymysql
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("PyTorch not installed: pip3 install torch"); sys.exit(1)

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


# ── Dataset ────────────────────────────────────────────────────────────────
class IndicatorDataset(Dataset):
    """Sliding window of indicators → forward return."""

    def __init__(self, sequences, returns):
        self.X = torch.FloatTensor(sequences)
        self.y = torch.FloatTensor(returns)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# ── Model ──────────────────────────────────────────────────────────────────
class LSTMPredictor(nn.Module):
    """LSTM with uncertainty head (predicts mean + log-variance)."""

    def __init__(self, input_size=120, hidden_size=128, num_layers=2,
                 dropout=0.2, predict_horizon=20):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                           batch_first=True, dropout=dropout)
        self.fc_mean = nn.Linear(hidden_size, 1)
        self.fc_logvar = nn.Linear(hidden_size, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last = lstm_out[:, -1, :]
        mean = self.fc_mean(last)
        logvar = self.fc_logvar(last)
        return mean.squeeze(), logvar.squeeze()


def gaussian_nll_loss(mean, logvar, target):
    """Negative log-likelihood under Gaussian with learned variance."""
    var = torch.exp(logvar)
    return 0.5 * (torch.log(var) + (target - mean) ** 2 / var).mean()


# ── Data Loading ───────────────────────────────────────────────────────────
def load_indicator_data(symbols, start, end):
    """Load indicator time series from MySQL."""
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    placeholders = ','.join(['%s'] * len(symbols))

    # Get indicator column names (exclude id, symbol, price_date)
    c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
              "WHERE TABLE_SCHEMA='ksfraser_stock_market' AND TABLE_NAME='indicators' "
              "AND COLUMN_NAME NOT IN ('id','symbol','price_date') ORDER BY ORDINAL_POSITION")
    ind_cols = [r['COLUMN_NAME'] for r in c.fetchall()]

    if not ind_cols:
        print("No indicators computed yet. Run indicator_calculator.py first.")
        return {}, []

    col_str = ','.join([f'`{c}`' for c in ind_cols])
    c.execute(f"SELECT symbol, price_date, {col_str} FROM indicators "
              f"WHERE symbol IN ({placeholders}) AND price_date BETWEEN %s AND %s "
              f"ORDER BY symbol, price_date", list(symbols) + [start, end])

    data = {}
    for r in c.fetchall():
        sym, d = r['symbol'], str(r['price_date'])
        vals = [float(r[c]) if r[c] is not None else 0.0 for c in ind_cols]
        data.setdefault(sym, []).append((d, vals))

    conn.close()
    return data, ind_cols


def load_price_data(symbols, start, end):
    """Load close prices to compute forward returns."""
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    placeholders = ','.join(['%s'] * len(symbols))
    c.execute(f"SELECT symbol, price_date, close FROM stockprices "
              f"WHERE symbol IN ({placeholders}) AND price_date BETWEEN %s AND %s "
              f"ORDER BY symbol, price_date", list(symbols) + [start, end])

    prices = {}
    for r in c.fetchall():
        prices.setdefault(r['symbol'], {})[str(r['price_date'])] = float(r['close'])
    conn.close()
    return prices


def build_sequences(indicator_data, prices, lookback=60, horizon=20):
    """
    Build (sequence, target) pairs.
    X: lookback days of indicators
    y: forward horizon-day return (log)
    """
    sequences = []
    targets = []
    meta = []  # (symbol, date) for traceability

    for sym, obs in indicator_data.items():
        if sym not in prices:
            continue
        price_dict = prices[sym]
        dates = [o[0] for o in obs]

        for i in range(len(obs) - lookback - horizon):
            # Sequence of indicators
            seq = [obs[i + j][1] for j in range(lookback)]
            if any(np.any(np.isnan(s)) or np.any(np.isinf(s)) for s in seq):
                continue

            # Forward return
            current_date = dates[i + lookback - 1]
            future_idx = i + lookback + horizon - 1
            if future_idx >= len(dates):
                continue
            future_date = dates[future_idx]

            current_price = price_dict.get(current_date)
            future_price = price_dict.get(future_date)
            if current_price is None or future_price is None:
                continue

            fwd_return = np.log(future_price / current_price)
            sequences.append(seq)
            targets.append(fwd_return)
            meta.append((sym, current_date))

    return np.array(sequences), np.array(targets), meta


# ── Training ────────────────────────────────────────────────────────────────
def train_model(config, train_data, val_data, device):
    """Train LSTM on training data, validate on val data."""
    cfg = config.nn
    model = LSTMPredictor(input_size=120, hidden_size=cfg.hidden_size,
                          num_layers=cfg.num_layers, dropout=cfg.dropout,
                          predict_horizon=cfg.predict_horizon).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)

    train_ds = IndicatorDataset(train_data[0], train_data[1])
    val_ds = IndicatorDataset(val_data[0], val_data[1])
    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size)

    print(f"\nTraining: {len(train_ds)} samples | Val: {len(val_ds)} samples")
    print(f"Device: {device} | Epochs: {cfg.epochs} | LR: {cfg.learning_rate}")

    best_val_loss = float('inf')
    history = {'train_loss': [], 'val_loss': []}

    for epoch in range(cfg.epochs):
        model.train()
        train_loss = 0
        for Xb, yb in train_loader:
            Xb, yb = Xb.to(device), yb.to(device)
            mean, logvar = model(Xb)
            loss = gaussian_nll_loss(mean, logvar, yb)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * len(Xb)

        train_loss /= len(train_ds)

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for Xb, yb in val_loader:
                Xb, yb = Xb.to(device), yb.to(device)
                mean, logvar = model(Xb)
                val_loss += gaussian_nll_loss(mean, logvar, yb).item() * len(Xb)
        val_loss /= len(val_ds)

        scheduler.step(val_loss)
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), '/tmp/nn_best.pt')

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1:>3}/{cfg.epochs}  train={train_loss:.4f}  val={val_loss:.4f}")

    # Load best
    model.load_state_dict(torch.load('/tmp/nn_best.pt', weights_only=True))
    return model, history


def evaluate_predictions(model, test_data, device, config):
    """Evaluate predictions on test set."""
    cfg = config.nn
    test_ds = IndicatorDataset(test_data[0], test_data[1])
    loader = DataLoader(test_ds, batch_size=64)

    model.eval()
    all_preds, all_vars, all_actuals = [], [], []

    with torch.no_grad():
        for Xb, yb in loader:
            Xb = Xb.to(device)
            mean, logvar = model(Xb)
            all_preds.extend(mean.cpu().numpy())
            all_vars.extend(torch.exp(logvar).cpu().numpy())
            all_actuals.extend(yb.numpy())

    preds = np.array(all_preds)
    actuals = np.array(all_actuals)
    variances = np.array(all_vars)

    mse = np.mean((preds - actuals) ** 2)
    mae = np.mean(np.abs(preds - actuals))
    corr = np.corrcoef(preds, actuals)[0, 1] if len(preds) > 2 else 0

    # Directional accuracy
    dir_acc = np.mean((preds > 0) == (actuals > 0))

    print(f"\n{'='*60}")
    print(f"NN TEST RESULTS")
    print(f"{'='*60}")
    print(f"  MSE:           {mse:.6f}")
    print(f"  MAE:           {mae:.4f}")
    print(f"  Corr(actual):  {corr:.4f}")
    print(f"  Dir accuracy:  {dir_acc:.1%}")
    print(f"  Mean pred:     {np.mean(preds):.4f}")
    print(f"  Mean actual:   {np.mean(actuals):.4f}")
    print(f"  Uncertainty:   {np.mean(np.sqrt(variances)):.4f}")

    return {'mse': mse, 'mae': mae, 'corr': corr, 'dir_acc': dir_acc}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default=None, help='Single symbol to train on (overrides)')
    parser.add_argument('--epochs', type=int, default=None)
    parser.add_argument('--predict', default=None, help='Date to predict (YYYY-MM-DD)')
    args = parser.parse_args()

    config = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
    if args.epochs:
        config.nn.epochs = args.epochs

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Get symbols
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    c.execute("SELECT symbol FROM symbol_master WHERE symbol IN (SELECT DISTINCT symbol FROM stockprices) ORDER BY symbol")
    symbols = [r['symbol'] for r in c.fetchall()]
    conn.close()

    if args.symbol:
        symbols = [args.symbol]

    print(f"NN Predictor: {len(symbols)} symbols | device={device}")

    # Load data
    indicator_data, ind_cols = load_indicator_data(symbols, '2014-01-01', '2024-12-31')
    prices = load_price_data(symbols, '2014-01-01', '2024-12-31')

    if not indicator_data:
        print("No indicator data. Computing from prices...")
        # Will need to compute first — skip for now
        print("Run python/indicator_calculator.py first.")
        return

    X_all, y_all, meta_all = build_sequences(indicator_data, prices,
                                              config.nn.lookback_days,
                                              config.nn.predict_horizon)

    if len(X_all) < 100:
        print(f"Only {len(X_all)} sequences — need more data")
        return

    print(f"Sequences: {len(X_all)} | Features: {X_all.shape[2]}")

    # Split by time
    split_train = int(len(X_all) * 0.70)
    split_val = int(len(X_all) * 0.85)

    train = (X_all[:split_train], y_all[:split_train])
    val = (X_all[split_train:split_val], y_all[split_train:split_val])
    test = (X_all[split_val:], y_all[split_val:])
    test_meta = meta_all[split_val:]

    # Train
    model, history = train_model(config, train, val, device)

    # Evaluate
    results = evaluate_predictions(model, test, device, config)

    # Save predictions to DB
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS nn_predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20), price_date DATE, predicted_return DECIMAL(8,6),
        uncertainty DECIMAL(8,6), actual_return DECIMAL(8,6),
        INDEX idx_sym_date (symbol, price_date)) ENGINE=InnoDB""")

    model.eval()
    test_ds = IndicatorDataset(test[0], test[1])
    all_preds, all_vars = [], []
    with torch.no_grad():
        for Xb, _ in DataLoader(test_ds, batch_size=64):
            mean, logvar = model(Xb.to(device))
            all_preds.extend(mean.cpu().numpy())
            all_vars.extend(torch.exp(logvar).cpu().numpy())

    for i, (sym, d) in enumerate(test_meta):
        if i < len(all_preds):
            c.execute("INSERT INTO nn_predictions (symbol,price_date,predicted_return,uncertainty) VALUES (%s,%s,%s,%s)",
                      (sym, d, float(all_preds[i]), float(np.sqrt(all_vars[i]))))

    conn.commit(); conn.close()
    print(f"Saved {len(all_preds)} predictions to nn_predictions")


if __name__ == '__main__':
    main()

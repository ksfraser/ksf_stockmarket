<?php
/** Manual OHLCV data entry + CSV import */
$message = $data['message'] ?? '';
$error   = $data['error'] ?? '';
$imported = $data['imported'] ?? 0;
$skipped  = $data['skipped'] ?? 0;
?>
<div class="card" id="manual-ohlcv-card">
    <div class="card-header">&#x1F4CB; Manual OHLCV Import</div>

    <?php if ($message): ?>
        <p style="color:var(--green);margin-bottom:12px;"><?= htmlspecialchars($message) ?></p>
    <?php endif; ?>
    <?php if ($error): ?>
        <p style="color:var(--red);margin-bottom:12px;"><?= htmlspecialchars($error) ?></p>
    <?php endif; ?>

    <!-- Single-row entry -->
    <form method="POST" action="?action=manual_ohlcv" style="margin-bottom:24px;">
        <h4 style="margin:0 0 8px 0;font-size:0.9em;color:var(--text2);">Single Row</h4>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
            <input type="text" name="single_symbol" placeholder="Symbol (e.g. AAMI.TO)" required
                   value="<?= htmlspecialchars($_GET['symbol'] ?? '') ?>"
                   style="width:120px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="date" name="single_date" required
                   style="width:140px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_open" placeholder="Open" class="price-field"
                   style="width:80px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_high" placeholder="High" class="price-field"
                   style="width:80px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_low" placeholder="Low" class="price-field"
                   style="width:80px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_close" placeholder="Close" required class="price-field"
                   style="width:80px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" name="single_volume" placeholder="Volume" class="price-field"
                   style="width:90px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_adj_close" placeholder="Adj Close" class="price-field"
                   style="width:90px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_dividend" placeholder="Dividend" class="price-field"
                   style="width:80px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <input type="number" step="any" name="single_split" placeholder="Split" class="price-field"
                   style="width:70px;padding:6px 10px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            <button type="submit" class="btn">Add Row</button>
        </div>
        <p style="font-size:0.8em;color:var(--text3);margin-top:6px;">
            Only Symbol, Date, and Close are required. Others default to NULL/0/1. Duplicates are skipped.
        </p>
    </form>

    <!-- CSV import -->
    <form method="POST" action="?action=manual_ohlcv" enctype="multipart/form-data">
        <h4 style="margin:0 0 8px 0;font-size:0.9em;color:var(--text2);">CSV Import</h4>
        <input type="file" name="csv_file" accept=".csv" required
               style="margin-bottom:8px;">
        <button type="submit" class="btn">Upload CSV</button>
        <p style="font-size:0.8em;color:var(--text3);margin-top:6px;">
            Accepted column names (case-insensitive, order doesn't matter):
            <code>symbol/ticker</code>, <code>date</code>, <code>close</code>, <code>open</code>, <code>high</code>, <code>low</code>,
            <code>volume/vol</code>, <code>adj close</code>, <code>dividend</code>, <code>split</code>.
            Duplicates are skipped.
        </p>
    </form>
</div>

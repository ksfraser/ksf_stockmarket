<?php
/**
 * Analysis Partial — Stock Analysis Writer Results (BR-7)
 *
 * Displays the latest `stock_analysis` row for the current symbol
 * on the stock detail page (`StockController::detail()`).
 *
 * Expected variables from controller:
 *   $symbol  — the stock symbol (e.g., 'CNR', 'GE')
 *   $this->pdo — PDO connection
 */
$analysis_rows = [];
try {
    $stmt = $this->pdo->prepare("
        SELECT symbol, period_type, period_date, writeup_text,
               created_at, updated_at, writer_version
        FROM stock_analysis
        WHERE symbol = :sym
        ORDER BY created_at DESC, period_date DESC
        LIMIT 1
    ");
    $stmt->execute([':sym' => $symbol]);
    $analysis_rows = $stmt->fetchAll();
} catch (Exception $e) {
    // Silently skip — analysis may not exist yet for this symbol
}

$latest_analysis = $analysis_rows ? $analysis_rows[0] : null;

if ($latest_analysis):
    $period_display = [
        'pre_earnings' => 'Pre-Earnings (2 weeks before)',
        'post_earnings' => 'Post-Earnings (3-5 days after)',
        'quarterly_check' => 'Quarterly Check',
        'atr' => 'ATR Review',
    ];
    $label = $period_display[$latest_analysis['period_type']] ?? ucfirst(str_replace('_', ' ', $latest_analysis['period_type']));
?>
<div class="analysis-section" style="margin-top:20px; padding:15px; background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px;">
    <h3 style="font-size:1.1em; margin-bottom:8px; color:#2c3e50;">
        📊 Latest Analysis Write-Up — <?= htmlspecialchars($label) ?>
        <span style="font-size:0.75em; color:#6c757d; float:right;">
            <?= htmlspecialchars($latest_analysis['period_date']) ?>
            <?= $latest_analysis['updated_at'] ? '(updated ' . htmlspecialchars(date('Y-m-d H:i', strtotime($latest_analysis['updated_at']))) . ')' : '' ?>
        </span>
    </h3>
    <?php if ($latest_analysis['writeup_text']): ?>
    <div style="font-size:0.9em; line-height:1.6; color:#333; white-space:pre-wrap;">
        <?= nl2br(htmlspecialchars($latest_analysis['writeup_text'])) ?>
    </div>
    <?php else: ?>
    <p style="font-style:italic; color:#6c757d; font-size:0.85em;">
        No detailed write-up available for this period. The analysis writer (`scripts/stock_analysis_writer.py`) can generate one — use `--pre`, `--post`, `--quarterly`, or `--atr` modes.
    </p>
    <?php endif; ?>
</div>
<?php else: ?>
<p style="font-style:italic; color:#777; font-size:0.85em; margin-top:10px;">
    No analysis write-ups found for <?= htmlspecialchars($symbol) ?>. The `scripts/stock_analysis_writer.py` can generate periodic write-ups (pre-earnings, post-earnings, quarterly, ATR). Run: `python3 scripts/stock_analysis_writer.py --quarterly --symbol <?= htmlspecialchars($symbol) ?>`
</p>
<?php endif; ?>

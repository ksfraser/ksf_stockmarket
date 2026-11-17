<?php
/**
 * Money & Risk Management Strategies page.
 *
 * Data:
 *   $strategies — array of money management strategy arrays (from Strategy->toArray())
 *   $totalCount
 */
$strategies = $data['strategies'] ?? [];
$totalCount = $data['totalCount'] ?? 0;
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4B0; Money &amp; Risk Management <span style="float:right;font-size:0.7em;color:var(--text3);"><?= (int)$totalCount ?> strategies</span></div>
    <p style="margin-bottom:12px;">
        Risk management is <strong>more important than entry signals</strong>.
        A mediocre strategy with excellent money management will outperform a great strategy with poor risk management.
        These strategies control position sizing, stop losses, and portfolio-level risk.
    </p>
    <div style="background:rgba(99,179,237,0.1);border:1px solid rgba(99,179,237,0.3);padding:12px;border-radius:var(--radius);margin-bottom:12px;">
        <strong>Key Principle:</strong> Always use the <em>more conservative</em> of two position sizing methods.
        If Kelly says 15% but fixed fractional says 2%, use 2%.
    </div>
</div>

<!-- Kelly Criterion Explainer (always show) -->
<div class="card" style="border-color:var(--accent);margin-bottom:20px;">
    <div class="card-header">&#x1F9EE; Kelly Criterion Quick Reference</div>
    <p>The Kelly Criterion determines the optimal position size to maximize long-term growth:</p>
    <div style="background:rgba(0,0,0,0.2);padding:14px;border-radius:var(--radius);font-family:monospace;text-align:center;margin:12px 0;font-size:1.1em;">
        f* = (b × p − q) / b
    </div>
    <ul style="margin-left:20px;font-size:0.9em;">
        <li><strong>f*</strong> = fraction of bankroll to bet</li>
        <li><strong>b</strong> = average win / average loss (the odds)</li>
        <li><strong>p</strong> = probability of winning</li>
        <li><strong>q</strong> = probability of losing (1 − p)</li>
    </ul>
    <div style="margin-top:12px;padding:12px;background:rgba(104,211,145,0.1);border-radius:var(--radius);border-left:3px solid var(--green);">
        <strong>Example:</strong> 55% win rate, avg win 1.5× avg loss → b=1.5, p=0.55<br>
        f* = (1.5 × 0.55 − 0.45) / 1.5 = 0.25<br>
        <strong>Use 25% of account</strong> (or <strong>12.5% for half-Kelly</strong>)
    </div>
    <p style="margin-top:12px;font-size:0.85em;color:var(--text3);">
        Win Rate Inversion: As win rate drops, required position size drops <em>non-linearly</em>.
        A 40% win rate strategy needs much smaller positions than 55%.
    </p>
</div>

<?php foreach ($strategies as $s):
    $statusColor = $s['status_color'] ?? 'green';
    $statusBg = match($statusColor) {
        'green' => 'rgba(104,211,145,0.2)',
        'yellow' => 'rgba(246,224,94,0.2)',
        'red' => 'rgba(252,129,129,0.2)',
        'accent' => 'rgba(99,179,237,0.2)',
        default => 'rgba(99,179,237,0.2)',
    };
    $statusFg = match($statusColor) {
        'green' => 'var(--green)',
        'yellow' => 'var(--yellow)',
        'red' => 'var(--red)',
        'accent' => 'var(--accent)',
        default => 'var(--accent)',
    };
    $bt = $s['backtest'] ?? [];
?>
<div class="card" style="margin-bottom:16px;">
    <div class="card-header">
        <span style="background:<?= $statusBg ?>;color:<?= $statusFg ?>;padding:2px 10px;border-radius:12px;font-size:0.75em;">
            <?= htmlspecialchars($s['status']) ?>
        </span>
        <?= htmlspecialchars($s['name']) ?>
        <?php if (($s['sleeve'] ?? '') === 'all'): ?>
            <span style="float:right;font-size:0.7em;background:rgba(99,179,237,0.15);color:var(--accent);padding:2px 8px;border-radius:8px;">All Sleeves</span>
        <?php endif; ?>
    </div>

    <p style="color:var(--text2);font-size:0.9em;margin-bottom:12px;"><?= htmlspecialchars($s['description']) ?></p>

    <?php if (!empty($s['criteria'])): ?>
    <div style="background:rgba(0,0,0,0.1);border-radius:var(--radius);padding:10px 14px;margin-bottom:12px;">
        <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:4px;">&#x1F4CB; Rules</div>
        <ul style="margin:0 0 0 16px;font-size:0.85em;line-height:1.6;">
            <?php foreach ($s['criteria'] as $c): ?><li><?= htmlspecialchars($c) ?></li><?php endforeach; ?>
        </ul>
    </div>
    <?php endif; ?>

    <?php if (!empty($bt['win_rate']) && $bt['win_rate'] !== 'N/A'): ?>
    <div class="grid-3" style="margin-bottom:12px;">
        <div style="background:rgba(0,0,0,0.1);padding:8px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.6em;color:var(--text3);text-transform:uppercase;">Win Rate</div>
            <div style="font-size:1.2em;font-weight:700;"><?= htmlspecialchars($bt['win_rate']) ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.1);padding:8px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.6em;color:var(--text3);text-transform:uppercase;">Profit Factor</div>
            <div style="font-size:1.2em;font-weight:700;"><?= htmlspecialchars($bt['profit_factor'] ?? 'N/A') ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.1);padding:8px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.6em;color:var(--text3);text-transform:uppercase;">Max DD</div>
            <div style="font-size:1.2em;font-weight:700;color:var(--red);"><?= htmlspecialchars($bt['max_drawdown'] ?? 'N/A') ?></div>
        </div>
    </div>
    <?php endif; ?>

    <?php if (!empty($bt['implications'])): ?>
    <div style="background:rgba(0,0,0,0.1);border-left:3px solid var(--green);padding:10px 14px;border-radius:0 var(--radius) var(--radius) 0;">
        <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:4px;">&#x1F4A1; Implications</div>
        <p style="font-size:0.85em;color:var(--text2);margin:0;"><?= htmlspecialchars($bt['implications']) ?></p>
    </div>
    <?php endif; ?>

    <?php if (!empty($s['sources'])): ?>
    <div style="font-size:0.7em;color:var(--text3);margin-top:6px;">
        Sources: <?= htmlspecialchars(implode(' &middot; ', $s['sources'])) ?>
    </div>
    <?php endif; ?>
</div>
<?php endforeach; ?>

<!-- Stop Methodology Explainer -->
<div class="card" style="border-color:var(--orange);margin-top:20px;margin-bottom:20px;">
    <div class="card-header">&#x26D4; Stop Methodology</div>
    <p>Every position should have <strong>two stops</strong>:</p>
    <ul style="margin-left:20px;font-size:0.9em;">
        <li><strong>Fixed Stop Loss:</strong> Maximum acceptable loss from cost basis (e.g., 15%). <em>This is your worst-case exit.</em></li>
        <li><strong>Trailing Stop:</strong> Dynamic stop that follows price up (e.g., 10% below recent high). This locks in profits.</li>
    </ul>
    <div style="margin:16px 0;padding:14px;background:rgba(237,137,54,0.1);border-radius:var(--radius);border-left:3px solid var(--orange);">
        <strong style="color:var(--orange);">&#x26A0;&#xFE0F; Rule: Once the trailing stop exceeds the fixed stop loss, the fixed stop becomes irrelevant.</strong>
    </div>
    <p><strong>ATR-Based Stop:</strong></p>
    <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:var(--radius);font-family:monospace;">
        Dynamic Stop = Price − (ATR(14) × Multiplier)<br>
        Apply: 2× ATR initially, tighten to 1× after 3× ATR profit
    </div>
</div>

<div style="display:flex;gap:12px;margin-top:24px;justify-content:center;">
    <a href="?action=strategy_stock" class="btn">&#x1F4CA; Stock Selection Strategies</a>
    <a href="?action=strategy_timing" class="btn">&#x23F0; Timing &amp; Technical</a>
</div>

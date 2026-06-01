<?php
/**
 * Money & Risk Management Strategies page — position sizing, stops, Kelly criterion.
 */
$strategies = $data['strategies'] ?? [];
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4B0; Money &amp; Risk Management — Overview</div>
    <p style="margin-bottom:12px;">
        Risk management is <strong>more important than entry signals</strong>.
        A mediocre strategy with excellent money management will outperform a great strategy with poor risk management.
        These strategies control position sizing, stop losses, and portfolio-level risk.
    </p>
    <div style="background:rgba(99,179,237,0.1);border:1px solid rgba(99,179,237,0.3);padding:12px;border-radius:var(--radius);margin-bottom:12px;">
        <strong>Key Principle:</strong> Always use the <em>more conservative</em> of two position sizing methods.
        If Kelly says 15% but fixed fractional says 2%, use 2%.
        This ensures survival during losing streaks.
    </div>
    <p style="font-size:0.85em;color:var(--text3);">
        <span style="color:var(--green);">&#x25CF;</span> Recommended &nbsp;
        <span style="color:var(--accent);">&#x25CF;</span> Active
    </p>
</div>

<!-- Kelly Criterion Explainer -->
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">&#x1F9EE; Kelly Criterion Quick Reference</div>
    <p>The Kelly Criterion determines the optimal position size to maximize long-term growth:</p>
    <div style="background:rgba(0,0,0,0.2);padding:14px;border-radius:var(--radius);font-family:monospace;text-align:center;margin:12px 0;font-size:1.1em;">
        f* = (b × p − q) / b
    </div>
    <p>Where:</p>
    <ul style="margin-left:20px;font-size:0.9em;">
        <li><strong>f*</strong> = fraction of bankroll to bet</li>
        <li><strong>b</strong> = average win / average loss (the odds)</li>
        <li><strong>p</strong> = probability of winning (win rate)</li>
        <li><strong>q</strong> = probability of losing (1 − p)</li>
    </ul>
    <div style="margin-top:12px;padding:12px;background:rgba(104,211,145,0.1);border-radius:var(--radius);border-left:3px solid var(--green);">
        <strong>Example:</strong> 55% win rate, avg win 1.5x avg loss → b=1.5, p=0.55, q=0.45<br>
        f* = (1.5 × 0.55 − 0.45) / 1.5 = (0.825 − 0.45) / 1.5 = 0.25<br>
        <strong>Use 25% of account</strong> (or <strong>12.5% for half-Kelly</strong> to be conservative)
    </div>
    <p style="margin-top:12px;font-size:0.85em;color:var(--text3);">
        Win Rate Inversion concept: As win rate drops, required position size drops faster.
        A 40% win rate strategy needs much smaller positions than a 55% strategy — the relationship is non-linear.
    </p>
</div>

<?php foreach ($strategies as $s): ?>
<div class="card">
    <div class="card-header">
        <?php
        $icon = match($s['status_color']) {
            'green' => '&#x2705;',
            'yellow' => '&#x26A0;&#xFE0F;',
            'red' => '&#x274C;',
            default => '&#x1F30A;',
        };
        echo $icon . ' ' . htmlspecialchars($s['name']);
        ?>
        <span style="float:right;font-size:0.75em;padding:2px 10px;border-radius:12px;
            background:<?php
                echo match($s['status_color']) {
                    'green' => 'rgba(104,211,145,0.2)',
                    'yellow' => 'rgba(246,224,94,0.2)',
                    'red' => 'rgba(252,129,129,0.2)',
                    default => 'rgba(99,179,237,0.2)',
                };
            ?>;
            color:<?php
                echo match($s['status_color']) {
                    'green' => 'var(--green)',
                    'yellow' => 'var(--yellow)',
                    'red' => 'var(--red)',
                    default => 'var(--accent)',
                };
            ?>;">
            <?php echo htmlspecialchars($s['status']); ?>
        </span>
    </div>

    <p style="margin-bottom:16px;color:var(--text2);"><?php echo htmlspecialchars($s['description']); ?></p>

    <div class="grid-3" style="margin-bottom:16px;">
        <div style="background:rgba(0,0,0,0.15);padding:12px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Win Rate</div>
            <div style="font-size:1.4em;font-weight:700;"><?php echo htmlspecialchars($s['win_rate']); ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.15);padding:12px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Profit Factor</div>
            <div style="font-size:1.4em;font-weight:700;"><?php echo htmlspecialchars($s['profit_factor']); ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.15);padding:12px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Max Drawdown</div>
            <div style="font-size:1.4em;font-weight:700;"><?php echo htmlspecialchars($s['max_drawdown']); ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.15);padding:12px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Avg Win</div>
            <div style="font-size:1.4em;font-weight:700;color:var(--green);"><?php echo htmlspecialchars($s['avg_win']); ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.15);padding:12px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Avg Loss</div>
            <div style="font-size:1.4em;font-weight:700;color:var(--red);"><?php echo htmlspecialchars($s['avg_loss']); ?></div>
        </div>
        <div style="background:rgba(0,0,0,0.15);padding:12px;border-radius:var(--radius);text-align:center;">
            <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;">Total Trades</div>
            <div style="font-size:1.4em;font-weight:700;"><?php echo number_format($s['total_trades']); ?></div>
        </div>
    </div>

    <div style="background:rgba(0,0,0,0.1);border-left:3px solid var(--accent);padding:12px 16px;border-radius:0 var(--radius) var(--radius) 0;margin-bottom:12px;">
        <div style="font-size:0.7em;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">&#x1F4A1; Implications</div>
        <p style="font-size:0.9em;color:var(--text2);margin:0;"><?php echo htmlspecialchars($s['implications']); ?></p>
    </div>

    <div style="font-size:0.75em;color:var(--text3);display:flex;gap:20px;">
        <span>&#x1F4C5; Last tested: <strong><?php echo htmlspecialchars($s['last_tested']); ?></strong></span>
        <span>&#x1F9F1; <?php echo htmlspecialchars($s['tested_by']); ?></span>
    </div>
</div>
<?php endforeach; ?>

<!-- Stop Methodology Explainer -->
<div class="card" style="border-color:var(--orange);margin-top:20px;">
    <div class="card-header">&#x26D4; Stop Methodology — When Trailing Stop Exceeds Fixed Stop</div>
    <p>Every position should have <strong>two stops</strong>:</p>
    <ul style="margin-left:20px;font-size:0.9em;">
        <li><strong>Fixed Stop Loss:</strong> Maximum acceptable loss from cost basis (e.g., 15%). <em>This is your worst-case exit.</em></li>
        <li><strong>Trailing Stop:</strong> Dynamic stop that follows price up (e.g., 10% below recent high). This locks in profits.</li>
    </ul>

    <div style="margin:16px 0;padding:14px;background:rgba(237,137,54,0.1);border-radius:var(--radius);border-left:3px solid var(--orange);">
        <strong style="color:var(--orange);">&#x26A0;&#xFE0F; Rule: Once the trailing stop exceeds the fixed stop loss, the fixed stop becomes irrelevant.</strong><br><br>
        Example: Bought at $100, fixed stop at $85.<br>
        Price rises to $130 → trailing stop (10%) = $117.<br>
        Price rises to $150 → trailing stop (10%) = $135.<br>
        At this point, the trailing stop ($135) is well above your fixed stop ($85).<br>
        The <strong>trailing stop will always trigger first</strong> — so you can safely ignore the fixed stop.
    </div>

    <div style="margin-top:12px;">
        <strong>ATR-Based Stop Calculation:</strong>
        <div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:var(--radius);font-family:monospace;margin-top:8px;">
            Dynamic Stop = Price − (ATR(14) × Multiplier)<br>
            Apply: 2× ATR initially, tighten to 1× after 3× ATR profit
        </div>
        <p style="font-size:0.85em;color:var(--text3);margin-top:8px;">
            ATR (Average True Range) measures volatility. In high-volatility stocks, stops widen to avoid noise.
            In low-volatility stocks, stops tighten. This self-adjusting mechanism is why we prefer ATR-based stops.
        </p>
    </div>
</div>

<div style="text-align:center;margin-top:20px;">
    <a href="?action=strategy_stock" class="btn">&larr; View Stock Selection Strategies</a>
</div>

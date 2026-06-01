<?php
/**
 * Stock Selection Strategies page — backtested results and methodology.
 */
$strategies = $data['strategies'] ?? [];
?>

<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F3AF; Stock Selection Strategies — Overview</div>
    <p style="margin-bottom:12px;">
        These strategies form the <strong>entry signal generation</strong> layer of the OWL ensemble.
        Each strategy has been backtested using <strong>walk-forward analysis</strong> to avoid future data peeking.
        Results shown are out-of-sample (the model never saw this data during training).
    </p>
    <p style="font-size:0.85em;color:var(--text3);">
        <span style="color:var(--green);">&#x25CF;</span> Battle Tested (production-ready) &nbsp;
        <span style="color:var(--yellow);">&#x25CF;</span> Promising (needs refinement) &nbsp;
        <span style="color:var(--red);">&#x25CF;</span> Needs Improvement &nbsp;
        <span style="color:var(--accent);">&#x25CF;</span> Active/Screening Tool
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
            default => '&#x1F4CA;',
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

<div style="text-align:center;margin-top:20px;">
    <a href="?action=strategy_money" class="btn">&rarr; View Money &amp; Risk Management Strategies</a>
</div>

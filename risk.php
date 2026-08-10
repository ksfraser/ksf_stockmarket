<?php
/**
 * Risk Manager Page
 */
$audit = $data['audit'] ?? [];
$gateResult = $data['gate_result'] ?? null;
?>
<div class="card">
    <div class="card-header">Risk Manager</div>
    
    <?php if ($gateResult): ?>
    <h3 style="margin-top:0;">Pre-Trade Check Result</h3>
    <div style="margin-bottom:16px;">
        <span style="font-size:1.5em;color:<?php echo $gateResult['verdict'] === 'APPROVED' ? '#4a4' : '#a44'; ?>;">
            <?php echo $gateResult['verdict']; ?>
        </span>
    </div>
    <table>
        <thead><tr><th>Check</th><th>Result</th><th>Detail</th></tr></thead>
        <tbody>
        <?php foreach ($gateResult['checks'] as $check): ?>
            <tr>
                <td><?php echo htmlspecialchars($check['name']); ?></td>
                <td style="color:<?php echo $check['result'] === 'PASS' ? '#4a4' : '#a44'; ?>;"><?php echo $check['result']; ?></td>
                <td class="text-muted"><?php echo htmlspecialchars($check['detail']); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php if ($gateResult['verdict'] === 'APPROVED'): ?>
        <p style="margin-top:16px;color:#4a4;">Position size: $<?php echo number_format($gateResult['position_size'], 2); ?></p>
    <?php endif; ?>
    
    <?php else: ?>
    
    <h3>Portfolio Risk Audit</h3>
    <?php if ($audit): ?>
    <div class="stats-grid" style="margin-bottom:16px;">
        <div class="stat-card">
            <div class="stat-value">$<?php echo number_format($audit['total_value'], 0); ?></div>
            <div class="stat-label">Total Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?php echo number_format($audit['total_risk_pct'], 1); ?>%</div>
            <div class="stat-label">Total Risk</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:<?php echo $audit['rating'] === 'GREEN' ? '#4a4' : '#cc9900'; ?>;">
                <?php echo $audit['rating']; ?>
            </div>
            <div class="stat-label">Rating</div>
        </div>
    </div>
    
    <?php if (!empty($audit['concentrations'])): ?>
    <h4>Concentrations</h4>
    <table>
        <thead><tr><th>Sector</th><th>Value</th></tr></thead>
        <tbody>
        <?php foreach ($audit['concentrations'] as $sector => $value): ?>
            <tr><td><?php echo htmlspecialchars($sector); ?></td>
                <td class="text-muted">$<?php echo number_format($value, 0); ?></td></tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
    <?php else: ?>
        <p class="text-muted">No positions to audit.</p>
    <?php endif; ?>
    
    <h3 style="margin-top:24px;">Pre-Trade Check</h3>
    <form method="POST" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;">
        <input type="hidden" name="action" value="risk">
        <div>
            <label>Symbol</label>
            <input type="text" name="symbol" placeholder="AAPL" required>
        </div>
        <div>
            <label>Direction</label>
            <select name="direction">
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
            </select>
        </div>
        <div>
            <label>Entry Price</label>
            <input type="number" name="entry_price" step="0.01" required>
        </div>
        <div>
            <label>Account Balance</label>
            <input type="number" name="account_balance" step="0.01" value="100000">
        </div>
        <div>
            <label>Daily P&L</label>
            <input type="number" name="daily_pnl" step="0.01" value="0">
        </div>
        <div>
            <label>Risk %</label>
            <input type="number" name="risk_pct" step="0.01" value="0.02">
        </div>
        <div style="grid-column:1/-1;">
            <button type="submit">Check Trade</button>
        </div>
    </form>
    <?php endif; ?>
</div>
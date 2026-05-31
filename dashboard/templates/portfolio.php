<?php
/**
 * Portfolio detail template.
 * Expects: $data = holdings, total_cost, total_value, total_pnl, total_pnl_pct
 */
?>
<div class="card">
    <div class="card-header">Portfolio Holdings</div>

    <div class="stats-grid" style="margin-bottom:20px">
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($data['total_value'], 2) ?></div>
            <div class="stat-label">Current Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($data['total_cost'], 2) ?></div>
            <div class="stat-label">Cost Basis</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?= $data['total_pnl'] >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                <?= $data['total_pnl'] >= 0 ? '+' : '' ?>$<?= number_format($data['total_pnl'], 2) ?>
            </div>
            <div class="stat-label">Total P&amp;L</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?= $data['total_pnl_pct'] >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                <?= $data['total_pnl_pct'] >= 0 ? '+' : '' ?><?= number_format($data['total_pnl_pct'], 2) ?>%
            </div>
            <div class="stat-label">Return</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Account</th>
                <th class="r">Shares</th>
                <th class="r">Cost Basis</th>
                <th class="r">Current Price</th>
                <th class="r">Market Value</th>
                <th class="r">P&amp;L</th>
                <th class="r">P&amp;L %</th>
                <th>Strategy</th>
                <th>Stop %</th>
                <th class="r">Allocation %</th>
                <th>Notes</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($data['holdings'] as $h):
            $currentValue = $h['shares'] * ($h['current_price'] ?? 0);
            $costTotal = $h['shares'] * $h['cost_basis'];
            $pnl = $currentValue - $costTotal;
            $pnlPct = $costTotal > 0 ? ($pnl / $costTotal) * 100 : 0;
            $allocPct = $data['total_value'] > 0 ? ($currentValue / $data['total_value']) * 100 : 0;
        ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?= urlencode($h['symbol']) ?>"><?= htmlspecialchars($h['symbol']) ?></a></strong></td>
                <td><?= htmlspecialchars($h['account_type']) ?></td>
                <td class="r"><?= number_format($h['shares'], 2) ?></td>
                <td class="r">$<?= number_format($h['cost_basis'], 2) ?></td>
                <td class="r"><?= fmt_price($h['current_price'] ?? null) ?></td>
                <td class="r">$<?= number_format($currentValue, 2) ?></td>
                <td class="r <?= $pnl >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= $pnl >= 0 ? '+' : '' ?>$<?= number_format($pnl, 2) ?></td>
                <td class="r <?= $pnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= fmt_pct($pnlPct) ?></td>
                <td><?= htmlspecialchars($h['strategy'] ?? '') ?></td>
                <td><?= $h['trailing_stop_pct'] ? ($h['trailing_stop_pct'] * 100) . '%' : '—' ?></td>
                <td class="r"><?= number_format($allocPct, 1) ?>%</td>
                <td class="text-muted" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap"><?= htmlspecialchars($h['notes'] ?? '') ?></td>
            </tr>

            <!-- Indicator summary row -->
            <?php if (!empty($h['indicators_preview'])): ?>
            <tr>
                <td colspan="12" style="padding:0">
                    <div style="padding:8px 12px; background:var(--bg3); display:flex; gap:20px; font-size:0.85em">
                        <?php foreach ($h['indicators_preview'] as $ik => $iv): ?>
                            <span><span class="text-muted"><?= htmlspecialchars($ik) ?>:</span> <?= is_numeric($iv) ? number_format($iv, 2) : htmlspecialchars($iv) ?></span>
                        <?php endforeach; ?>
                        <a href="?action=indicators&symbol=<?= urlencode($h['symbol']) ?>" style="margin:left:auto">View All Indicators &rarr;</a>
                    </div>
                </td>
            </tr>
            <?php endif; ?>

        <?php endforeach; ?>
        </tbody>
        <tfoot>
            <tr style="font-weight:700; background:var(--bg3)">
                <td colspan="5">TOTAL</td>
                <td class="r">$<?= number_format($data['total_value'], 2) ?></td>
                <td class="r <?= $data['total_pnl'] >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= $data['total_pnl'] >= 0 ? '+' : '' ?>$<?= number_format($data['total_pnl'], 2) ?></td>
                <td class="r <?= $data['total_pnl_pct'] >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= fmt_pct($data['total_pnl_pct']) ?></td>
                <td colspan="3"></td>
            </tr>
        </tfoot>
    </table>
</div>

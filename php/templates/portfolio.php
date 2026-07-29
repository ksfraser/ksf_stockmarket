<?php
/**
 * Portfolio detail template — enhanced v2.
 * Expects: $data = holdings, total_cost, total_value, total_pnl, total_pnl_pct,
 *          total_annualized_pnl_pct, account_filter, account_types
 */
$data = $data ?? [];
$holdings = $data['holdings'] ?? [];
$totalCost = $data['total_cost'] ?? 0;
$totalValue = $data['total_value'] ?? 0;
$totalPnl = $data['total_pnl'] ?? 0;
$totalPnlPct = $data['total_pnl_pct'] ?? 0;
$totalAnnPnlPct = $data['total_annualized_pnl_pct'] ?? 0;
$accountFilter = $data['account_filter'] ?? 'all';
$accountTypes = $data['account_types'] ?? [];

// Safety score tooltip explanation
$SAFETY_TOOLTIP = "Dividend Safety Score (0-100): Based on payout ratio, " .
    "earnings coverage, debt levels, and dividend growth consistency. " .
    "80+ = Excellent, 60-79 = Good, 40-59 = Caution, <40 = High Risk";
?>

<div class="card">
    <div class="card-header">Portfolio Holdings</div>

    <!-- Account filter -->
    <form method="GET" class="search-bar" style="margin-bottom:16px">
        <input type="hidden" name="action" value="portfolio">
        <label style="font-size:0.85em; color:var(--text3); margin-right:8px">Registration:</label>
        <select name="account" onchange="this.form.submit()">
            <option value="all" <?= $accountFilter === 'all' ? 'selected' : '' ?>>All Registrations</option>
            <?php foreach ($accountTypes as $at): ?>
                <option value="<?= htmlspecialchars($at) ?>" <?= $accountFilter === $at ? 'selected' : '' ?>>
                    <?= htmlspecialchars($at) ?>
                </option>
            <?php endforeach; ?>
        </select>

        <?php
        $accounts = $data['portfolio_accounts'] ?? [];
        if (!empty($accounts)):
        ?>
        &nbsp;
        <label style="font-size:0.85em; color:var(--text3); margin-right:8px">Account:</label>
        <select name="account_id" onchange="this.form.submit()">
            <option value="">All Accounts</option>
            <?php foreach ($accounts as $a): ?>
                <option value="<?= (int)$a['id'] ?>" <?= ($_GET['account_id'] ?? '') == $a['id'] ? 'selected' : '' ?>>
                    <?= htmlspecialchars($a['institution']) ?> — <?= htmlspecialchars($a['account_nickname']) ?> (<?= htmlspecialchars($a['registration_type']) ?>)
                </option>
            <?php endforeach; ?>
        </select>
        <?php endif; ?>

        <a href="?action=portfolio_transfers" style="float:right; font-size:0.85em;">Transfer totals</a>
    </form>

    <?php include $GLOBALS['APP_ROOT'] . '/templates/partials/trade_guidance.php'; ?>

    <!-- Summary stats -->
    <div class="stats-grid" style="margin-bottom:20px">
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($totalValue, 2) ?></div>
            <div class="stat-label">Current Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$<?= number_format($totalCost, 2) ?></div>
            <div class="stat-label">Cost Basis</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?= $totalPnl >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                <?= $totalPnl >= 0 ? '+' : '' ?>$<?= number_format($totalPnl, 2) ?>
            </div>
            <div class="stat-label">Total P&amp;L</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?= $totalPnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                <?= $totalPnlPct >= 0 ? '+' : '' ?><?= number_format($totalPnlPct, 2) ?>%
            </div>
            <div class="stat-label">Return</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?= $totalAnnPnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                <?= $totalAnnPnlPct >= 0 ? '+' : '' ?><?= number_format($totalAnnPnlPct, 2) ?>%
            </div>
            <div class="stat-label">Annualized Return</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$<?php echo number_format((float)($available_cash ?? 0), 2); ?></div>
            <div class="stat-label">Available Cash (T+2)</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Account</th>
                <th class="r">Shares</th>
                <th class="r">Cost Basis</th>
                <th class="r">Current</th>
                <th class="r">Market Value</th>
                <th class="r">P&amp;L</th>
                <th class="r">P&amp;L %</th>
                <th class="r">Ann. P&amp;L %</th>
                <th>Strategy / Stops</th>
                <th class="r">Alloc %</th>
                <th class="r">Cost Alloc %</th>
                <th>P/E</th>
                <th>Div Yield</th>
                <th>Cost Yield</th>
                <th>Safety</th>
                <th>Taxonomies</th>
                <th>Settlement</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($holdings as $h):
            $currentValue = $h['current_value'] ?? 0;
            $costTotal = $h['cost_total'] ?? 0;
            $pnl = $h['pnl'] ?? 0;
            $pnlPct = $h['pnl_pct'] ?? 0;
            $annPnlPct = $h['annualized_pnl_pct'] ?? null;
            $allocPct = $totalValue > 0 ? ($currentValue / $totalValue) * 100 : 0;
            $costAllocPct = $totalCost > 0 ? ($costTotal / $totalCost) * 100 : 0;
            $pe = $h['pe'] ?? null;
            $divYield = $h['div_yield'] ?? null;
            $costBasisDivYield = $h['cost_basis_div_yield'] ?? null;
            $safety = $h['dividend_safety']['score'] ?? null;
            $safetyRating = $h['dividend_safety']['rating'] ?? null;
            $stopStatus = $h['stop_status'] ?? 'na';
            $effectiveStop = $h['effective_stop_price'] ?? 0;
            $trailingStop = $h['trailing_stop_price'] ?? 0;
            $stopLoss = $h['stop_loss_price'] ?? 0;
            $atr14 = $h['atr_14'] ?? null;
            $atrMult = $h['atr_multiplier'] ?? 2.0;
            $strategy = $h['strategy'] ?? 'Trailing Stop';
            $taxonomies = $h['taxonomies'] ?? [];
            $settlementDate = $h['settlement_date'] ?? null;

            // Stop color: green=safe, yellow=within 2%, red=breach
            $stopColor = $stopStatus === 'breach' ? 'var(--red)' : ($stopStatus === 'warning' ? 'var(--yellow)' : 'var(--green)');
            $stopIcon = $stopStatus === 'breach' ? '&#x26A0;' : ($stopStatus === 'warning' ? '&#x26A0;' : '&#x2713;');
        ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?= urlencode($h['symbol']) ?>"><?= htmlspecialchars($h['symbol']) ?></a></strong></td>
                <td>
                    <?php
                    $parts = explode(', ', $h['accounts']);
                    echo implode(' | ', array_map(function($p){
                        return htmlspecialchars(str_replace('|', ' — ', $p));
                    }, $parts));
                    ?>
                </td>
                <td class="r"><?= number_format($h['shares'], 2) ?></td>
                <td class="r">$<?= number_format($h['cost_basis'], 2) ?></td>
                <td class="r"><?= fmt_price($h['current_price'] ?? null) ?></td>
                <td class="r">$<?= number_format($currentValue, 2) ?></td>
                <td class="r <?= $pnl >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= $pnl >= 0 ? '+' : '' ?>$<?= number_format($pnl, 2) ?></td>
                <td class="r <?= $pnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= fmt_pct($pnlPct) ?></td>
                <td class="r <?= ($annPnlPct ?? 0) >= 0 ? 'pnl-positive' : 'pnl-negative' ?>">
                    <?= $annPnlPct !== null ? number_format($annPnlPct, 1) . '%' : '—' ?>
                </td>
                <td style="font-size:0.82em; white-space:nowrap">
                    <div><strong><?= htmlspecialchars($strategy) ?></strong></div>
                    <div style="color:var(--text3)">
                        Trail: <?= number_format($h['trailing_stop_pct'], 1) ?>% ($<?= number_format($trailingStop, 2) ?>)
                    </div>
                    <div style="color:var(--text3)">
                        Stop: <?= number_format($h['stop_loss_pct'], 1) ?>% ($<?= number_format($stopLoss, 2) ?>)
                    </div>
                    <?php if ($atr14): ?>
                    <div style="color:var(--text3)">
                        ATR(14): $<?= number_format($atr14, 2) ?> (<?= $atrMult ?>x)
                    </div>
                    <?php endif; ?>
                    <div style="color:<?= $stopColor ?>; font-weight:600">
                        <?= $stopIcon ?> Eff.Stop: $<?= number_format($effectiveStop, 2) ?>
                    </div>
                </td>
                <td class="r"><?= number_format($allocPct, 1) ?>%</td>
                <td class="r"><?= number_format($costAllocPct, 1) ?>%</td>
                <td><?= $pe ? number_format($pe, 1) : '—' ?></td>
                <td><?= $divYield !== null ? number_format($divYield, 2) . '%' : '—' ?></td>
                <td><?= $costBasisDivYield !== null ? number_format($costBasisDivYield, 2) . '%' : '—' ?></td>
                <td>
                    <?php if ($safety !== null): ?>
                        <span title="<?= htmlspecialchars($SAFETY_TOOLTIP) ?>"
                              style="cursor:help; color:<?= $safety >= 80 ? 'var(--green)' : ($safety >= 60 ? 'var(--yellow)' : 'var(--red)') ?>">
                            <?= $safety ?> <span style="font-size:0.8em; color:var(--text3)">(<?= $safetyRating ?>)</span>
                            <span style="font-size:0.7em; color:var(--text3)">&#x24D8;</span>
                        </span>
                    <?php else: ?>—<?php endif; ?>
                </td>
                <td style="font-size:0.82em">
                    <?php if (!empty($taxonomies)): ?>
                        <?php foreach ($taxonomies as $tag): ?>
                            <span style="display:inline-block;background:var(--bg3);color:var(--text);padding:2px 8px;border-radius:12px;font-size:0.75em;margin:2px 2px 2px 0;border:1px solid var(--border)"><?= htmlspecialchars($tag) ?></span>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </td>
                <td class="r"><?= $settlementDate ? htmlspecialchars($settlementDate) : '—' ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
        <tfoot>
            <tr style="font-weight:700; background:var(--bg3)">
                <td colspan="7">TOTAL</td>
                <td class="r">$<?= number_format($totalValue, 2) ?></td>
                <td class="r <?= $totalPnl >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= $totalPnl >= 0 ? '+' : '' ?>$<?= number_format($totalPnl, 2) ?></td>
                <td class="r <?= $totalPnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= fmt_pct($totalPnlPct) ?></td>
                <td class="r <?= $totalAnnPnlPct >= 0 ? 'pnl-positive' : 'pnl-negative' ?>"><?= $totalAnnPnlPct >= 0 ? '+' : '' ?><?= number_format($totalAnnPnlPct, 1) ?>%</td>
                <td colspan="8"></td>
            </tr>
        </tfoot>
    </table>
</div>

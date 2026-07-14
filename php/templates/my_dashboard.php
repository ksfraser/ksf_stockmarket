<?php
/**
 * My Dashboard — personalized user dashboard with buy/sell recs,
 * upcoming earnings, dividend dates, portfolio movers, data coverage.
 */
$recs = $data['recommendations'] ?? [];
$earnings = $data['upcoming_earnings'] ?? [];
$divDates = $data['dividend_dates'] ?? [];
$movers = $data['portfolio_movers'] ?? ['gainers' => [], 'losers' => []];
$coverage = $data['coverage'] ?? ['total' => 0, 'with_prices' => 0, 'with_indicators' => 0, 'total_rows' => 0];
$settings = $data['settings'] ?? [];
$portfolioSummary = $data['portfolio_summary'] ?? null;
?>

<!-- Portfolio Summary (User's Holdings) -->
<?php if ($portfolioSummary): ?>
<div class="card" style="border-color:var(--accent);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div>
            <h2 style="margin:0;font-size:1.3em;">&#x1F4CA; My Portfolio</h2>
            <p style="margin:4px 0 0;font-size:0.85em;color:var(--text3);">
                Personal holdings summary &mdash; <a href="?action=portfolio" style="color:var(--accent);">View full portfolio &rarr;</a>
            </p>
        </div>
        <a href="?action=overview" style="font-size:0.85em;color:var(--accent);">&larr; Switch to App Dashboard</a>
    </div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">$<?php echo number_format($portfolioSummary['market_value'] ?? 0, 0); ?></div>
            <div class="stat-label">Current Value</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$<?php echo number_format($portfolioSummary['cost_basis'] ?? 0, 0); ?></div>
            <div class="stat-label">Cost Basis</div>
        </div>
        <div class="stat-card">
            <div class="stat-value <?php echo (($portfolioSummary['pnl'] ?? 0) >= 0) ? 'pnl-positive' : 'pnl-negative'; ?>">
                <?php echo (($portfolioSummary['pnl'] ?? 0) >= 0) ? '+' : ''; ?>$<?php echo number_format($portfolioSummary['pnl'] ?? 0, 0); ?>
                <span style="font-size:0.7em;">(<?php echo (($portfolioSummary['pnl_pct'] ?? 0) >= 0) ? '+' : ''; ?><?php echo number_format($portfolioSummary['pnl_pct'] ?? 0, 1); ?>%)</span>
            </div>
            <div class="stat-label">Unrealized P&amp;L</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?php echo $portfolioSummary['num_holdings'] ?? 0; ?></div>
            <div class="stat-label">Holdings</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="font-size:1.1em;"><?php echo number_format($portfolioSummary['top_pnl_pct'] ?? 0, 1); ?>%</div>
            <div class="stat-label">Best Performer</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="font-size:1.1em;"><?php echo number_format($portfolioSummary['worst_pnl_pct'] ?? 0, 1); ?>%</div>
            <div class="stat-label">Worst Performer</div>
        </div>
    </div>
</div>
<?php endif; ?>

<!-- Buy/Sell Recommendations -->
<div class="card">
    <div class="card-header">&#x1F4C8; Buy / Sell Recommendations</div>
    <?php if (empty($recs)): ?>
        <p class="text-muted">No recommendations available.</p>
    <?php else: ?>
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th class="r">Price</th>
                <th class="c">Date</th>
                <th class="r">Shares</th>
                <th class="r">Cost</th>
                <th class="r">RSI</th>
                <th>Signal</th>
                <th class="c">Zacks</th>
                <th class="c">Exit Risk</th>
                <th>Reasons</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($recs as $r):
            $signalClass = match(true) {
                str_contains($r['action'], 'STRONG BUY') => 'green',
                str_contains($r['action'], 'BUY') => 'green',
                str_contains($r['action'], 'STRONG SELL') => 'red',
                str_contains($r['action'], 'SELL') => 'red',
                default => ''
            };
            $zacks = $r['zacks_score'] ?? [];
            $zacksRank = $zacks['rank'] ?? '—';
            $zacksRankText = $zacks['rank_text'] ?? '—';
            $zacksColor = [1=>'var(--green)',2=>'var(--green)',3=>'var(--yellow)',4=>'var(--red)',5=>'var(--red)'][$zacksRank] ?? 'var(--text3)';
            $exit = $r['exit_signals'] ?? [];
            $exitComposite = $exit['composite_exit_risk'] ?? '—';
            $exitPct = is_numeric($exitComposite) ? round($exitComposite * 100, 0) . '%' : '—';
        ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?php echo $r['symbol']; ?>"><?php echo $r['symbol']; ?></a></strong></td>
                <td class="r">$<?php echo number_format($r['current_price'] ?? 0, 2); ?></td>
                <td class="c"><?php echo $r['price_date'] ? date('M j', strtotime($r['price_date'])) : '—'; ?></td>
                <td class="r"><?php echo number_format($r['shares'], 2); ?></td>
                <td class="r">$<?php echo number_format($r['cost_basis'], 2); ?></td>
                <td class="r"><?php echo $r['rsi'] ? number_format($r['rsi'], 1) : '—'; ?></td>
                <td class="<?php echo $signalClass; ?>"><strong><?php echo $r['action']; ?></strong></td>
                <td class="c" style="color:<?php echo $zacksColor ?>"><strong><?php echo htmlspecialchars($zacksRankText); ?></strong></td>
                <td class="c"><?php echo $exitPct; ?></td>
                <td style="font-size:0.82em;color:var(--text3);"><?php echo htmlspecialchars(implode(', ', $r['reasons'])); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
</div>

<div class="grid-2">
    <!-- Upcoming Earnings -->
    <div class="card">
        <div class="card-header">&#x1F4C5; Upcoming Earnings</div>
        <?php if (empty($earnings)): ?>
            <p class="text-muted">No upcoming earnings data available.</p>
        <?php else: ?>
        <table>
            <thead><tr><th>Symbol</th><th class="c">Date</th><th class="r">EPS Est.</th></tr></thead>
            <tbody>
            <?php foreach ($earnings as $e): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?php echo $e['symbol']; ?>"><?php echo $e['symbol']; ?></a></td>
                    <td class="c"><?php echo date('M j', strtotime($e['earnings_date'])); ?></td>
                    <td class="r"><?php echo $e['eps_estimate'] ? '$' . number_format($e['eps_estimate'], 2) : '—'; ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>

    <!-- Dividend Dates -->
    <div class="card">
        <div class="card-header">&#x1F4B0; Upcoming Dividends</div>
        <?php if (empty($divDates)): ?>
            <p class="text-muted">No upcoming dividend dates available.</p>
        <?php else: ?>
        <table>
            <thead><tr><th>Symbol</th><th class="c">Ex-Date</th><th class="r">Rate</th><th class="r">Yield</th></tr></thead>
            <tbody>
            <?php foreach ($divDates as $d): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?php echo $d['symbol']; ?>"><?php echo $d['symbol']; ?></a></td>
                    <td class="c"><?php echo date('M j', strtotime($d['ex_dividend_date'])); ?></td>
                    <td class="r">$<?php echo number_format($d['dividend_rate'] ?? 0, 3); ?></td>
                    <td class="r"><?php echo $d['dividend_yield'] ? number_format($d['dividend_yield'], 2) . '%' : '—'; ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>
</div>

<!-- Top Gainers & Losers (Portfolio) -->
<div class="grid-2">
    <div class="card">
        <div class="card-header">&#x2191; Top Gainers (Portfolio)</div>
        <?php if (empty($movers['gainers'])): ?>
            <p class="text-muted">No gainers today.</p>
        <?php else: ?>
        <table>
            <thead><tr><th>Symbol</th><th class="r">Price</th><th class="c">Date</th><th class="r">Change</th></tr></thead>
            <tbody>
            <?php foreach ($movers['gainers'] as $m): ?>
                    <tr>
                    <td><a href="?action=detail&symbol=<?php echo $m['symbol']; ?>"><?php echo $m['symbol']; ?></a></td>
                    <td class="r">$<?php echo number_format($m['current_price'] ?? 0, 2); ?></td>
                    <td class="c"><?php echo $m['price_date'] ? date('M j', strtotime($m['price_date'])) : '—'; ?></td>
                    <td class="r green">+<?php echo number_format($m['change_pct'], 2); ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>
    <div class="card">
        <div class="card-header">&#x2193; Top Losers (Portfolio)</div>
        <?php if (empty($movers['losers'])): ?>
            <p class="text-muted">No losers today.</p>
        <?php else: ?>
        <table>
            <thead><tr><th>Symbol</th><th class="r">Price</th><th class="c">Date</th><th class="r">Change</th></tr></thead>
            <tbody>
            <?php foreach ($movers['losers'] as $m): ?>
                <tr>
                    <td><a href="?action=detail&symbol=<?php echo $m['symbol']; ?>"><?php echo $m['symbol']; ?></a></td>
                    <td class="r">$<?php echo number_format($m['current_price'] ?? 0, 2); ?></td>
                    <td class="c"><?php echo $m['price_date'] ? date('M j', strtotime($m['price_date'])) : '—'; ?></td>
                    <td class="r red"><?php echo number_format($m['change_pct'], 2); ?>%</td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>
</div>

<!-- Data Coverage (Portfolio) -->
<div class="card">
    <div class="card-header">&#x1F4CA; Data Coverage — Portfolio Symbols</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value"><?php echo $coverage['total']; ?></div>
            <div class="stat-label">Portfolio Symbols</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?php echo $coverage['with_prices']; ?></div>
            <div class="stat-label">With Prices</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?php echo $coverage['with_indicators']; ?></div>
            <div class="stat-label">With Indicators</div>
        </div>
        <div class="stat-card">
            <div class="stat-value"><?php echo number_format($coverage['total_rows']); ?></div>
            <div class="stat-label">Total Price Rows</div>
        </div>
    </div>
</div>

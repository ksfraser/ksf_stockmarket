<?php
$exitSignals = $data['exit_signals'] ?? [];
$exitRisk = $exitSignals['composite_exit_risk'] ?? null;
$exitDetails = $exitSignals['individual_signals'] ?? [];
$exitWeights = $exitSignals['signal_weights'] ?? [];
$exitTriggered = $exitSignals['n_signals_triggered'] ?? 0;
$exitTotal = $exitSignals['n_signals_total'] ?? 0;

$signalMeta = [
    'trailing_stop_breach' => ['Trailing Stop Breach', 'Price below ATR-based trailing stop (3×ATR from 60d high)'],
    'rsi_overbought' => ['RSI Overbought', 'RSI(14) above 65 — momentum overextended'],
    'ma200_breakdown' => ['200D MA Breakdown', 'Price below 95% of 200-day SMA — long-term trend broken'],
    'bb_upper_touch' => ['Bollinger Band Upper Touch', 'Price at >95% of BB(20,2) range — overextended'],
    'roe_deterioration' => ['ROE Deterioration', 'Return on Equity below 10% — quality declining'],
    'debt_equity_rise' => ['Debt/Equity Rise', 'D/E ratio above 0.6 — leverage increasing'],
    'fcf_negative' => ['FCF Negative', 'Free Cash Flow negative — cash burn'],
    'pe_extreme' => ['P/E Extreme', 'Trailing P/E above 25× — valuation stretched'],
    'insider_selling' => ['Insider Selling', 'Insider sell ratio >50% in 90 days'],
    'corporate_event_risk' => ['Corporate Event Risk', 'Merger/acquisition/restructuring pending'],
    'sector_underperformance' => ['Sector Underperformance', 'Stock lagging sector ETF by >10%'],
    'fcf_yield_low' => ['FCF Yield Low', 'FCF/Market Cap below 2% — poor cash generation'],
    'earnings_drop' => ['Earnings Drop', 'Quarterly EPS declined >20% QoQ'],
    'dividend_cut' => ['Dividend Cut', 'Dividend reduced vs prior period'],
    'yield_on_cost_low' => ['Yield on Cost Low', 'Yield on cost below 1.5%'],
    'debt_ebitda_high' => ['Debt/EBITDA High', 'Debt/EBITDA above 4× — leverage risk'],
    'management_change' => ['Management Change', 'CEO/CFO departure — execution risk'],
    'cash_burn' => ['Cash Burn', 'Cash runway <4 quarters at current burn rate'],
];
?>
<?php if ($exitRisk !== null): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Exit Signal Risk Assessment <span class="text-muted" style="font-size:0.8em; font-weight:normal;">(InvestorsObserver 18 Warning Signs)</span></div>
    <div style="display:flex; gap:20px; align-items:center; margin-bottom:12px;">
        <div style="font-size:2.5em; font-weight:700; color:<?= $exitRisk >= 0.6 ? 'var(--red)' : ($exitRisk >= 0.3 ? 'var(--yellow)' : 'var(--green)') ?>">
            <?= round($exitRisk * 100) ?>%
        </div>
        <div style="font-size:0.9em; color:var(--text2);">
            <strong><?= $exitTriggered ?></strong> of <strong><?= $exitTotal ?></strong> signals triggered
        </div>
    </div>
    <?php if (!empty($exitDetails)): ?>
    <div style="overflow-x:auto;">
    <table style="width:100%; border-collapse:collapse; font-size:0.85em;">
        <thead>
            <tr style="background:var(--bg2); border-bottom:2px solid var(--border);">
                <th style="padding:8px; text-align:left;">Indicator</th>
                <th style="padding:8px; text-align:center;">Value</th>
                <th style="padding:8px; text-align:center;">Weight</th>
                <th style="padding:8px; text-align:center;">Signal</th>
                <th style="padding:8px; text-align:left;">Indicator</th>
                <th style="padding:8px; text-align:center;">Value</th>
                <th style="padding:8px; text-align:center;">Weight</th>
                <th style="padding:8px; text-align:center;">Signal</th>
            </tr>
        </thead>
        <tbody>
            <?php
            $signals = array_keys($exitDetails);
            $half = ceil(count($signals) / 2);
            for ($i = 0; $i < $half; $i++):
                $left = $signals[$i] ?? null;
                $right = $signals[$i + $half] ?? null;
            ?>
            <tr style="border-bottom:1px solid var(--border);">
                <?php if ($left): 
                    $triggered = $exitDetails[$left];
                    $weight = $exitWeights[$left] ?? 0;
                    $meta = $signalMeta[$left] ?? [$left, ''];
                    $color = $triggered ? 'var(--red)' : 'var(--green)';
                    $icon = $triggered ? '⚠ SELL' : '✓ OK';
                ?>
                <td style="padding:6px 8px; font-weight:500;" title="<?= htmlspecialchars($meta[1]) ?>"><?= htmlspecialchars($meta[0]) ?></td>
                <td style="padding:6px 8px; text-align:center;"><?= isset($exitDetails[$left]) ? ($exitDetails[$left] ? '1.00' : '0.00') : '—' ?></td>
                <td style="padding:6px 8px; text-align:center;"><?= round($weight * 100) ?>%</td>
                <td style="padding:6px 8px; text-align:center; color:<?= $color ?>; font-weight:600;"><?= $icon ?></td>
                <?php else: ?>
                <td colspan="4" style="padding:6px 8px;">&nbsp;</td>
                <?php endif; ?>
                <?php if ($right): 
                    $triggered = $exitDetails[$right];
                    $weight = $exitWeights[$right] ?? 0;
                    $meta = $signalMeta[$right] ?? [$right, ''];
                    $color = $triggered ? 'var(--red)' : 'var(--green)';
                    $icon = $triggered ? '⚠ SELL' : '✓ OK';
                ?>
                <td style="padding:6px 8px; font-weight:500;" title="<?= htmlspecialchars($meta[1]) ?>"><?= htmlspecialchars($meta[0]) ?></td>
                <td style="padding:6px 8px; text-align:center;"><?= isset($exitDetails[$right]) ? ($exitDetails[$right] ? '1.00' : '0.00') : '—' ?></td>
                <td style="padding:6px 8px; text-align:center;"><?= round($weight * 100) ?>%</td>
                <td style="padding:6px 8px; text-align:center; color:<?= $color ?>; font-weight:600;"><?= $icon ?></td>
                <?php else: ?>
                <td colspan="4" style="padding:6px 8px;">&nbsp;</td>
                <?php endif; ?>
            </tr>
            <?php endfor; ?>
        </tbody>
    </table>
    </div>
    <?php endif; ?>
</div>
<?php endif; ?>

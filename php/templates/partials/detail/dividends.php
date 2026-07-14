<?php if (!empty($dividends) || !empty($dividendSafety)): ?>
<div class="card" style="margin-top:12px;">
    <div class="card-header">Dividend Details</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
            <h4>Dividend Safety Score: <span style="color:<?= ($dividendSafety['score'] ?? 0) >= 80 ? 'var(--green)' : (($dividendSafety['score'] ?? 0) >= 60 ? 'var(--yellow)' : 'var(--red)') ?>"><?= $dividendSafety['score'] ?? 'N/A' ?></span> <span style="font-size:0.8em; color:var(--text3)">(<?= $dividendSafety['rating'] ?? 'N/A' ?>)</span></h4>
            <table style="width:100%; font-size:0.9em;">
                <tr><td class="text-muted">Payout Ratio</td><td class="r"><?= isset($fundamentals['payout_ratio']) ? number_format($fundamentals['payout_ratio'], 1) . '%' : '—' ?></td></tr>
                <tr><td class="text-muted">FCF Coverage</td><td class="r"><?= $dividendSafety['fcf_coverage'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">D/E Ratio</td><td class="r"><?= $dividendSafety['debt_equity'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">Revenue Growth</td><td class="r"><?= $dividendSafety['revenue_growth'] ?? '—' ?></td></tr>
                <tr><td class="text-muted">Annual Dividend</td><td class="r">$<?= number_format($fundamentals['dividend_rate'] ?? 0, 2) ?></td></tr>
                <tr><td class="text-muted">5Y Avg Yield</td><td class="r"><?= isset($fundamentals['five_year_div_yield']) ? number_format($fundamentals['five_year_div_yield'], 2) . '%' : '—' ?></td></tr>
            </table>
        </div>
        <div>
            <h4>Recent Dividends</h4>
            <table style="width:100%; font-size:0.9em;">
                <thead><tr><th>Date</th><th class="r">Amount</th><th class="r">Yield</th></tr></thead>
                <tbody>
                <?php foreach (array_slice($dividends, 0, 8) as $d): ?>
                    <tr>
                        <td><?= $d['ex_date'] ?></td>
                        <td class="r">$<?= number_format($d['amount'] ?? 0, 4) ?></td>
                        <td class="r"><?= $close > 0 && $d['amount'] ? number_format(($d['amount'] * 4) / $close * 100, 2) . '%' : '—' ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>
<?php endif; ?>

<?php
$rows = $data['rows'] ?? [];
$sortField = $data['sort_field'] ?? 'symbol';
$sortDir = $data['sort_dir'] ?? 'asc';
$nextDir = $data['next_dir'] ?? 'desc';
$asOf = $data['as_of'] ?? '-';
$error = $data['error'] ?? null;

function sortLink(string $field, string $label, string $currentSort, string $nextDir): string {
    $arrow = '';
    if ($currentSort === $field) {
        $arrow = $nextDir === 'asc' ? ' ▲' : ' ▼';
    }
    return '<a href="?action=etf_performance&sort=' . urlencode($field) . '&dir=' . ($currentSort === $field && $nextDir === 'asc' ? 'desc' : 'asc') . '" class="sort-link">' . htmlspecialchars($label) . $arrow . '</a>';
}

function fmtPct(?float $v): string {
    if ($v === null || $v === '') return '-';
    $cls = $v >= 0 ? 'pos' : 'neg';
    return '<span class="' . $cls . '">' . number_format($v, 1) . '%</span>';
}
?>
<div class="card" id="etf-perf-card">
    <div class="card-header">📈 ETF Performance Screener</div>
    <?php if ($error): ?>
        <p class="text-muted" style="color:var(--red);"><?php echo htmlspecialchars($error); ?></p>
    <?php else: ?>
        <p class="subtitle">As of: <?php echo htmlspecialchars($asOf); ?> | Click column headers to sort</p>

        <div style="overflow-x:auto;">
            <table>
                <thead>
                    <tr>
                        <th><?php echo sortLink('symbol','Symbol',$sortField,$nextDir); ?></th>
                        <th><?php echo sortLink('name','Name',$sortField,$nextDir); ?></th>
                        <th><?php echo sortLink('category','Category',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('1M','1M',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('3M','3M',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('6M','6M',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('9M','9M',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('12M','12M',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('1Y','1Y',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('2Y','2Y',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('3Y','3Y',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('5Y','5Y',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('10Y','10Y',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('yield_12m','Yield%',$sortField,$nextDir); ?></th>
                        <th class="r"><?php echo sortLink('expense_ratio','MER%',$sortField,$nextDir); ?></th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($rows as $r): ?>
                    <tr>
                        <td><a href="?action=detail&symbol=<?php echo htmlspecialchars($r['symbol']); ?>"><?php echo htmlspecialchars($r['symbol']); ?></a></td>
                        <td><?php echo htmlspecialchars($r['name'] ?? $r['symbol']); ?></td>
                        <td class="cat"><?php echo htmlspecialchars($r['category'] ?? 'ETF'); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_1M'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_3M'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_6M'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_9M'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_12M'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_1Y'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_2Y'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_3Y'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_5Y'] ?? null); ?></td>
                        <td class="r"><?php echo fmtPct($r['p_10Y'] ?? null); ?></td>
                        <td class="r"><?php echo number_format((float)($r['yield_12m'] ?? 0), 2); ?>%</td>
                        <td class="r"><?php echo number_format((float)($r['expense_ratio'] ?? 0), 2); ?>%</td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    <?php endif; ?>
</div>

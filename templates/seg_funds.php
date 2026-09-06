<?php
/**
 * Segregated Funds list template.
 * Expects: $data from SegFundsController::listFunds()
 * Renders BR-11/FR-11 filter boxes (risk/death/maturity + return-quintile buckets).
 */
$funds = $data['funds'] ?? [];
$carriers = $data['carriers'] ?? [];
$categories = $data['categories'] ?? [];
$seriesList = $data['seriesList'] ?? [];
$filter_carrier = $data['filter_carrier'] ?? '';
$filter_category = $data['filter_category'] ?? '';
$filter_series = $data['filter_series'] ?? '';
$search = $data['search'] ?? '';
$filter_risk = $data['filter_risk_rating'] ?? [];
$filter_death = $data['filter_death_pct'] ?? [];
$filter_mat = $data['filter_mat_pct'] ?? [];
$filter_b1y = $data['filter_bucket_1y'] ?? '';
$filter_b5y = $data['filter_bucket_5y'] ?? '';
$filter_b10y = $data['filter_bucket_10y'] ?? '';
$filter_bytd = $data['filter_bucket_ytd'] ?? '';
$bucketLabels = $data['bucket_labels'] ?? [];
$sortBy = $data['sortBy'] ?? 'fund_name';
$sortDir = $data['sortDir'] ?? 'ASC';
$total_active = $data['total_active'] ?? 0;
$total_carriers = $data['total_carriers'] ?? 0;

/** Build a bucket dropdown <select> from NTILE boundaries */
function bucket_options(string $key, string $current, array $bucketLabels): string {
    if (empty($bucketLabels[$key])) return '';
    $html = '<select name="' . htmlspecialchars($key) . '" id="filter_' . htmlspecialchars($key) . '" onchange="applyFilters()">';
    $html .= '<option value="">All</option>';
    foreach ($bucketLabels[$key] as $b) {
        $q = (int)$b['q'];
        $lo = $b['lo'] !== null ? number_format((float)$b['lo'], 1) : '—';
        $hi = $b['hi'] !== null ? number_format((float)$b['hi'], 1) : '—';
        $n = (int)$b['n'];
        $label = "Q{$q} ({$lo}–{$hi}%, {$n})";
        $sel = ($current === "Q{$q}" || $current === (string)$q) ? ' selected' : '';
        $html .= '<option value="Q' . $q . '"' . $sel . '>' . htmlspecialchars($label) . '</option>';
    }
    $html .= '</select>';
    return $html;
}

function sort_link($label, $field, $sortBy, $sortDir, $params) {
    $newDir = ($sortBy === $field && $sortDir === 'ASC') ? 'DESC' : 'ASC';
    $params['sort'] = $field;
    $params['dir'] = $newDir;
    $url = '?' . http_build_query(array_merge(['action' => 'seg_funds'], $params));
    $arrow = '';
    if ($sortBy === $field) {
        $arrow = $sortDir === 'ASC' ? ' ▲' : ' ▼';
    }
    return '<a href="' . htmlspecialchars($url) . '">' . htmlspecialchars($label) . $arrow . '</a>';
}

// Build a params array for sort links that preserves current filters
$filterParams = [];
if ($filter_carrier) $filterParams['carrier'] = $filter_carrier;
if ($filter_category) $filterParams['category'] = $filter_category;
if ($filter_series) $filterParams['series'] = $filter_series;
if ($search) $filterParams['search'] = $search;
if ($filter_risk) $filterParams['risk'] = $filter_risk;
if ($filter_death) $filterParams['death'] = $filter_death;
if ($filter_mat) $filterParams['maturity'] = $filter_mat;
if ($filter_b1y) $filterParams['bucket_1y'] = $filter_b1y;
if ($filter_b5y) $filterParams['bucket_5y'] = $filter_b5y;
if ($filter_b10y) $filterParams['bucket_10y'] = $filter_b10y;
if ($filter_bytd) $filterParams['bucket_ytd'] = $filter_bytd;

$riskValues = ['Low', 'Low-Med', 'Medium', 'Med-High', 'High'];
$benefitValues = [75, 100];
$bucketCols = ['bucket_1y' => '1Y', 'bucket_5y' => '5Y', 'bucket_10y' => '10Y', 'bucket_ytd' => 'YTD'];
?>

<div class="card">
    <div class="card-header">
        Segregated Funds
        <span class="badge"><?= number_format($total_active) ?> funds</span>
        <span class="badge"><?= $total_carriers ?> carriers</span>
    </div>

    <!-- Filters -->
    <div class="search-bar" style="display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end;padding:8px;">
        <div>
            <label style="font-size:0.75em;color:var(--text3);">Search</label><br>
            <input type="text" name="search" value="<?= htmlspecialchars($search) ?>"
                   placeholder="Fund or carrier..." id="searchInput"
                   onkeyup="if(event.key==='Enter') applyFilters()">
        </div>

        <div>
            <label style="font-size:0.75em;color:var(--text3);">Carrier</label><br>
            <select name="carrier" id="filterCarrier" onchange="applyFilters()">
                <option value="">All</option>
                <?php foreach ($carriers as $c): ?>
                    <option value="<?= htmlspecialchars($c) ?>" <?= $filter_carrier === $c ? 'selected' : '' ?>><?= htmlspecialchars($c) ?></option>
                <?php endforeach; ?>
            </select>
        </div>

        <div>
            <label style="font-size:0.75em;color:var(--text3);">Category</label><br>
            <select name="category" id="filterCategory" onchange="applyFilters()">
                <option value="">All</option>
                <?php foreach ($categories as $c): ?>
                    <option value="<?= htmlspecialchars($c) ?>" <?= $filter_category === $c ? 'selected' : '' ?>><?= htmlspecialchars($c) ?></option>
                <?php endforeach; ?>
            </select>
        </div>

        <div>
            <label style="font-size:0.75em;color:var(--text3);">Risk Rating</label><br>
            <select name="risk[]" id="filterRisk" onchange="applyFilters()" multiple size="1" style="min-width:100px;">
                <?php foreach ($riskValues as $r): ?>
                    <option value="<?= $r ?>" <?= in_array($r, $filter_risk) ? 'selected' : '' ?>><?= $r ?></option>
                <?php endforeach; ?>
            </select>
        </div>

        <div>
            <label style="font-size:0.75em;color:var(--text3);">Death %</label><br>
            <select name="death[]" id="filterDeath" onchange="applyFilters()" multiple size="1" style="min-width:70px;">
                <?php foreach ($benefitValues as $v): ?>
                    <option value="<?= $v ?>" <?= in_array($v, $filter_death) ? 'selected' : '' ?>><?= $v ?>%</option>
                <?php endforeach; ?>
            </select>
        </div>

        <div>
            <label style="font-size:0.75em;color:var(--text3);">Maturity %</label><br>
            <select name="maturity[]" id="filterMaturity" onchange="applyFilters()" multiple size="1" style="min-width:70px;">
                <?php foreach ($benefitValues as $v): ?>
                    <option value="<?= $v ?>" <?= in_array($v, $filter_mat) ? 'selected' : '' ?>><?= $v ?>%</option>
                <?php endforeach; ?>
            </select>
        </div>

        <?php foreach ($bucketCols as $key => $label): ?>
        <div>
            <label style="font-size:0.75em;color:var(--text3);"><?= $label ?></label><br>
            <?= bucket_options($key, ${"filter_b" . substr($key, 7)}, $bucketLabels) ?>
        </div>
        <?php endforeach; ?>

        <div>
            <button class="btn btn-sm" onclick="applyFilters()">Filter</button>
            <a href="?action=seg_funds" class="btn btn-sm">Clear</a>
        </div>
    </div>

    <!-- Table -->
    <table>
        <thead>
            <tr>
                <th><?= sort_link('Fund Name', 'fund_name', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Carrier', 'carrier', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Category', 'category', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Series', 'series', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Risk', 'risk_rating', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="c">Death %</th>
                <th class="c">Mat %</th>
                <th class="r"><?= sort_link('MER %', 'mer', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('1Y %', 'return_1yr', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('3Y %', 'return_3yr', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('5Y %', 'return_5yr', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('10Y %', 'return_10yr', $sortBy, $sortDir, $filterParams) ?></th>
            </tr>
        </thead>
        <tbody>
        <?php if (empty($funds)): ?>
            <tr><td colspan="12" class="c text-muted" style="padding:40px">No funds found</td></tr>
        <?php else: ?>
        <?php foreach ($funds as $f): ?>
            <tr>
                <td><strong><a href="?action=seg_fund_detail&id=<?= (int)$f['id'] ?>"><?= htmlspecialchars($f['fund_name']) ?></a></strong></td>
                <td><?= htmlspecialchars($f['carrier']) ?></td>
                <td class="text-muted"><?= htmlspecialchars($f['category'] ?? '') ?></td>
                <td class="text-muted"><?= htmlspecialchars($f['series'] ?? '') ?></td>
                <td class="c"><?= htmlspecialchars($f['risk_rating'] ?? '—') ?></td>
                <td class="c"><?= $f['death_benefit_pct'] !== null ? (int)$f['death_benefit_pct'] . '%' : '—' ?></td>
                <td class="c"><?= $f['maturity_benefit_pct'] !== null ? (int)$f['maturity_benefit_pct'] . '%' : '—' ?></td>
                <td class="r"><?= $f['mer'] !== null ? number_format((float)$f['mer'], 2) : '—' ?></td>
                <td class="r <?= ($f['return_1yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $f['return_1yr'] !== null ? number_format((float)$f['return_1yr'], 1) : '—' ?></td>
                <td class="r <?= ($f['return_3yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $f['return_3yr'] !== null ? number_format((float)$f['return_3yr'], 1) : '—' ?></td>
                <td class="r <?= ($f['return_5yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $f['return_5yr'] !== null ? number_format((float)$f['return_5yr'], 1) : '—' ?></td>
                <td class="r <?= ($f['return_10yr'] ?? 0) >= 0 ? 'text-green' : 'text-red' ?>"><?= $f['return_10yr'] !== null ? number_format((float)$f['return_10yr'], 1) : '—' ?></td>
            </tr>
        <?php endforeach; ?>
        <?php endif; ?>
        </tbody>
    </table>
</div>

<script>
function applyFilters() {
    const params = new URLSearchParams();
    params.set('action', 'seg_funds');
    const get = (id) => document.getElementById(id)?.value || '';
    const search = get('searchInput');
    const carrier = get('filterCarrier');
    const category = get('filterCategory');
    if (search) params.set('search', search);
    if (carrier) params.set('carrier', carrier);
    if (category) params.set('category', category);

    // Multi-select arrays
    const riskSel = document.getElementById('filterRisk');
    if (riskSel) Array.from(riskSel.selectedOptions).forEach(o => params.append('risk[]', o.value));
    const deathSel = document.getElementById('filterDeath');
    if (deathSel) Array.from(deathSel.selectedOptions).forEach(o => params.append('death[]', o.value));
    const matSel = document.getElementById('filterMaturity');
    if (matSel) Array.from(matSel.selectedOptions).forEach(o => params.append('maturity[]', o.value));

    // Buckets
    ['bucket_1y', 'bucket_5y', 'bucket_10y', 'bucket_ytd'].forEach(k => {
        const el = document.getElementById('filter_' + k);
        if (el && el.value) params.set(k, el.value);
    });

    // Sort
    const url = new URLSearchParams(window.location.search);
    if (url.get('sort')) params.set('sort', url.get('sort'));
    if (url.get('dir')) params.set('dir', url.get('dir'));
    window.location.href = '?' + params.toString();
}
</script>

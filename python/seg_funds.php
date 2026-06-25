<?php
/**
 * Segregated Funds list template.
 * Expects: $data from SegFundsController::listFunds()
 */
$funds = $data['funds'] ?? [];
$carriers = $data['carriers'] ?? [];
$categories = $data['categories'] ?? [];
$seriesList = $data['seriesList'] ?? [];
$filter_carrier = $data['filter_carrier'] ?? '';
$filter_category = $data['filter_category'] ?? '';
$filter_series = $data['filter_series'] ?? '';
$search = $data['search'] ?? '';
$sortBy = $data['sortBy'] ?? 'fund_name';
$sortDir = $data['sortDir'] ?? 'ASC';
$total_active = $data['total_active'] ?? 0;
$total_carriers = $data['total_carriers'] ?? 0;

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

$filterParams = [];
if ($filter_carrier) $filterParams['carrier'] = $filter_carrier;
if ($filter_category) $filterParams['category'] = $filter_category;
if ($filter_series) $filterParams['series'] = $filter_series;
if ($search) $filterParams['search'] = $search;
?>

<div class="card">
    <div class="card-header">
        Segregated Funds
        <span class="badge"><?= number_format($total_active) ?> funds</span>
        <span class="badge"><?= $total_carriers ?> carriers</span>
    </div>

    <!-- Filters -->
    <div class="search-bar">
        <input type="text" name="search" value="<?= htmlspecialchars($search) ?>"
               placeholder="Search fund or carrier..." id="searchInput"
               onkeyup="if(event.key==='Enter') applyFilters()">

        <select name="carrier" id="filterCarrier" onchange="applyFilters()">
            <option value="">All Carriers</option>
            <?php foreach ($carriers as $c): ?>
                <option value="<?= htmlspecialchars($c) ?>" <?= $filter_carrier === $c ? 'selected' : '' ?>><?= htmlspecialchars($c) ?></option>
            <?php endforeach; ?>
        </select>

        <select name="category" id="filterCategory" onchange="applyFilters()">
            <option value="">All Categories</option>
            <?php foreach ($categories as $c): ?>
                <option value="<?= htmlspecialchars($c) ?>" <?= $filter_category === $c ? 'selected' : '' ?>><?= htmlspecialchars($c) ?></option>
            <?php endforeach; ?>
        </select>

        <select name="series" id="filterSeries" onchange="applyFilters()">
            <option value="">All Series</option>
            <?php foreach ($seriesList as $s): ?>
                <option value="<?= htmlspecialchars($s) ?>" <?= $filter_series === $s ? 'selected' : '' ?>><?= htmlspecialchars($s) ?></option>
            <?php endforeach; ?>
        </select>

        <button class="btn btn-sm" onclick="applyFilters()">Filter</button>
        <a href="?action=seg_funds" class="btn btn-sm">Clear</a>
    </div>

    <!-- Table -->
    <table>
        <thead>
            <tr>
                <th><?= sort_link('Fund Name', 'fund_name', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Carrier', 'carrier', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Category', 'category', $sortBy, $sortDir, $filterParams) ?></th>
                <th><?= sort_link('Series', 'series', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('MER %', 'mer', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('1Y %', 'return_1yr', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('3Y %', 'return_3yr', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('5Y %', 'return_5yr', $sortBy, $sortDir, $filterParams) ?></th>
                <th class="r"><?= sort_link('10Y %', 'return_10yr', $sortBy, $sortDir, $filterParams) ?></th>
            </tr>
        </thead>
        <tbody>
        <?php if (empty($funds)): ?>
            <tr><td colspan="9" class="c text-muted" style="padding:40px">No funds found</td></tr>
        <?php else: ?>
        <?php foreach ($funds as $f): ?>
            <tr>
                <td><strong><a href="?action=seg_fund_detail&id=<?= (int)$f['id'] ?>"><?= htmlspecialchars($f['fund_name']) ?></a></strong></td>
                <td><?= htmlspecialchars($f['carrier']) ?></td>
                <td class="text-muted"><?= htmlspecialchars($f['category'] ?? '') ?></td>
                <td><?= htmlspecialchars($f['series'] ?? '') ?></td>
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
    const search = document.getElementById('searchInput').value;
    const carrier = document.getElementById('filterCarrier').value;
    const category = document.getElementById('filterCategory').value;
    const series = document.getElementById('filterSeries').value;
    if (search) params.set('search', search);
    if (carrier) params.set('carrier', carrier);
    if (category) params.set('category', category);
    if (series) params.set('series', series);
    window.location = '?' + params.toString();
}
</script>

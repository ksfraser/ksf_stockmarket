<?php
/**
 * Symbol list template.
 * Expects: $data from StockController::listSymbols()
 */
$symbols = $data['symbols'] ?? [];
$search    = $data['search']    ?? '';
$exchange  = $data['exchange']  ?? '';
$sortBy    = $data['sortBy']    ?? 'symbol';
$sortDir   = $data['sortDir']   ?? 'ASC';
$page      = (int)($data['page'] ?? 1);
$perPage   = (int)($data['per_page'] ?? 200);
$totalAll  = (int)($data['total_all'] ?? 0);
$totalPages = (int)($data['total_pages'] ?? 1);

$start = ($page - 1) * $perPage + 1;
$end   = min($page * $perPage, $totalAll);

$preserve = [
    'action'   => 'list',
    'search'   => $search,
    'exchange' => $exchange,
    'sort'     => $sortBy,
    'dir'      => $sortDir,
    'page'     => $page,
    'per_page' => $perPage,
];
$baseQs = http_build_query(array_diff_key($preserve, ['page' => $page]));

function pageLinkList(int $targetPage, string $queryString, int $currentPage): string
{
    if ($targetPage < 1) return '#';
    $qs = preg_replace('/&?page=\d+/', '', $queryString);
    $qs = trim($qs, '&');
    $qs = $qs ? $qs . '&page=' . $targetPage : 'page=' . $targetPage;
    return '?' . $qs;
}

$perPageOptions = [50, 100, 250, 500, 1000];
$sortLink = fn($field) => '?action=list&sort=' . $field . '&dir=' . (($sortBy === $field && $sortDir === 'ASC') ? 'DESC' : 'ASC') . '&search=' . urlencode($search) . '&exchange=' . urlencode($exchange) . '&per_page=' . $perPage;
?>
<div class="card">
    <div class="card-header">All Symbols (<?= $totalAll ?>)</div>

    <?php if (($data['current_user']['role'] ?? '') === 'admin'): ?>
    <div style="margin-bottom:12px; display:flex; align-items:center; gap:12px; padding:8px 12px; background:rgba(0,0,0,0.15); border-radius:6px;">
        <form method="GET" action="?action=refresh_all_prices" style="display:flex; align-items:center; gap:8px;">
            <input type="hidden" name="redirect" value="?<?= htmlspecialchars($baseQs) ?>">
            <label style="font-size:0.85em; display:flex; align-items:center; gap:4px; cursor:pointer;">
                <input type="checkbox" name="full_history" value="1" onchange="var btn=this.form.querySelector('button'); btn.textContent=this.checked?'Refresh All History':'Refresh Recent Gap'">
                All History
            </label>
            <button type="submit" class="btn btn-sm" style="background:var(--orange);">Refresh Recent Gap</button>
        </form>
        <span style="font-size:0.75em; color:var(--text3);">Admin only</span>
    </div>
    <?php endif; ?>

    <div class="search-bar">
        <input type="text" name="search" value="<?= htmlspecialchars($search) ?>"
               placeholder="Search symbol or name..." id="searchInput"
               onkeyup="if(event.key==='Enter') window.location='?action=list&search='+encodeURIComponent(this.value)">
        <select name="exchange" onchange="window.location='?action=list&exchange='+encodeURIComponent(this.value)">
            <option value="">All Exchanges</option>
            <option value="TSX" <?= $exchange === 'TSX' ? 'selected' : '' ?>>TSX</option>
            <option value="NYSE" <?= $exchange === 'NYSE' ? 'selected' : '' ?>>NYSE</option>
            <option value="NASDAQ" <?= $exchange === 'NASDAQ' ? 'selected' : '' ?>>NASDAQ</option>
        </select>
        <button class="btn btn-sm" onclick="window.location='?action=list&search='+encodeURIComponent(document.getElementById('searchInput').value)">Search</button>
        <a href="?action=list" class="btn btn-sm">Clear</a>
    </div>

    <!-- Toolbar: page size + pager summary -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <form method="GET" style="display:inline-flex; align-items:center; gap:6px; font-size:0.85em;">
            <input type="hidden" name="action" value="list">
            <input type="hidden" name="search" value="<?= htmlspecialchars($search) ?>">
            <input type="hidden" name="exchange" value="<?= htmlspecialchars($exchange) ?>">
            <input type="hidden" name="sort" value="<?= htmlspecialchars($sortBy) ?>">
            <input type="hidden" name="dir" value="<?= htmlspecialchars($sortDir) ?>">
            <input type="hidden" name="page" value="1">
            <label>Show</label>
            <select name="per_page" onchange="this.form.submit()">
                <?php foreach ($perPageOptions as $opt): ?>
                    <option value="<?= $opt ?>" <?= $perPage === $opt ? 'selected' : '' ?>><?= $opt ?></option>
                <?php endforeach; ?>
            </select>
            <span class="muted">per page</span>
        </form>

        <div style="display:flex; align-items:center; gap:8px; font-size:0.85em;">
            <span class="muted">Showing <?= $start ?>–<?= $end ?> of <?= $totalAll ?></span>
            <a href="<?= pageLinkList($page - 1, $baseQs, $page) ?>" class="btn btn-sm" style="<?= $page <= 1 ? 'opacity:0.4;pointer-events:none;' : '' ?>">◀ Prev</a>
            <span style="color:var(--text2);">Page <?= $page ?> / <?= $totalPages ?></span>
            <a href="<?= pageLinkList($page + 1, $baseQs, $page) ?>" class="btn btn-sm" style="<?= $page >= $totalPages ? 'opacity:0.4;pointer-events:none;' : '' ?>">Next ▶</a>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th><a href="<?= $sortLink('symbol') ?>">Symbol</a></th>
                <th>Name</th>
                <th>Exchange</th>
                <th>Sector</th>
                <th class="r"><a href="<?= $sortLink('close') ?>">Close</a></th>
                <th class="r"><a href="<?= $sortLink('volume') ?>">Volume</a></th>
                <th class="r"><a href="<?= $sortLink('change_pct') ?>">Change</a></th>
                <th class="r"><a href="<?= $sortLink('price_date') ?>">Last Date</a></th>
            </tr>
        </thead>
        <tbody>
        <?php if (empty($symbols)): ?>
            <tr><td colspan="8" class="c text-muted" style="padding:40px">No symbols found</td></tr>
        <?php else: ?>
        <?php foreach ($symbols as $s): ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?= urlencode($s['symbol']) ?>" style="color:var(--text);text-decoration:none;"><?= htmlspecialchars($s['symbol']) ?></a></strong></td>
                <td class="text-muted"><?= htmlspecialchars($s['name'] ?? '') ?></td>
                <td><?= htmlspecialchars($s['exchange'] ?? '') ?></td>
                <td class="text-muted"><?= htmlspecialchars($s['sector'] ?? '') ?></td>
                <td class="r"><?= fmt_price($s['close'], $s['prev_close'] ?? null) ?></td>
                <td class="r"><?= fmt_num($s['volume'] ?? 0) ?></td>
                <td class="r"><?= fmt_pct($s['change_pct'] ?? null) ?></td>
                <td class="r text-muted"><?= fmt_date($s['price_date']) ?></td>
            </tr>
        <?php endforeach; ?>
        <?php endif; ?>
        </tbody>
    </table>

    <!-- Bottom pager -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; flex-wrap:wrap; gap:8px;">
        <span class="muted" style="font-size:0.85em;">Showing <?= $start ?>–<?= $end ?> of <?= $totalAll ?></span>
        <div style="display:flex; gap:6px; align-items:center;">
            <a href="<?= pageLinkList($page - 1, $baseQs, $page) ?>" class="btn btn-sm" style="<?= $page <= 1 ? 'opacity:0.4;pointer-events:none;' : '' ?>">◀ Prev</a>
            <span style="color:var(--text2); font-size:0.85em;">Page <?= $page ?> of <?= $totalPages ?></span>
            <a href="<?= pageLinkList($page + 1, $baseQs, $page) ?>" class="btn btn-sm" style="<?= $page >= $totalPages ? 'opacity:0.4;pointer-events:none;' : '' ?>">Next ▶</a>
        </div>
    </div>
</div>

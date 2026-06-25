<?php
/**
 * Symbol list template.
 * Expects: $data['symbols'] = array of symbol rows
 */
$symbols = $data['symbols'] ?? [];
$search = $_GET['search'] ?? '';
$exchange = $_GET['exchange'] ?? '';
$sortBy = $_GET['sort'] ?? 'symbol';
$sortDir = $_GET['dir'] ?? 'ASC';
?>

<div class="card">
    <div class="card-header">All Symbols (<?= count($symbols) ?>)</div>

    <?php if (($data['current_user']['role'] ?? '') === 'admin'): ?>
    <div style="margin-bottom:12px; display:flex; align-items:center; gap:12px; padding:8px 12px; background:rgba(0,0,0,0.15); border-radius:6px;">
        <form method="GET" action="?action=refresh_all_prices" style="display:flex; align-items:center; gap:8px;">
            <input type="hidden" name="redirect" value="?action=list">
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
               onkeyup="if(event.key==='Enter') window.location='?action=list&search='+this.value">
        <select name="exchange" onchange="window.location='?action=list&exchange='+this.value">
            <option value="">All Exchanges</option>
            <option value="TSX" <?= $exchange === 'TSX' ? 'selected' : '' ?>>TSX</option>
            <option value="NYSE" <?= $exchange === 'NYSE' ? 'selected' : '' ?>>NYSE</option>
            <option value="NASDAQ" <?= $exchange === 'NASDAQ' ? 'selected' : '' ?>>NASDAQ</option>
        </select>
        <button class="btn btn-sm" onclick="window.location='?action=list&search='+document.getElementById('searchInput').value">Search</button>
        <a href="?action=list" class="btn btn-sm">Clear</a>
    </div>

    <table>
        <thead>
            <tr>
                <th><a href="?action=list&sort=symbol&dir=<?= $sortBy==='symbol' && $sortDir==='ASC' ? 'DESC' : 'ASC' ?>&search=<?= urlencode($search) ?>&exchange=<?= urlencode($exchange) ?>">Symbol</a></th>
                <th>Name</th>
                <th>Exchange</th>
                <th>Sector</th>
                <th class="r"><a href="?action=list&sort=close&dir=<?= $sortBy==='close' && $sortDir==='ASC' ? 'DESC' : 'ASC' ?>&search=<?= urlencode($search) ?>&exchange=<?= urlencode($exchange) ?>">Close</a></th>
                <th class="r"><a href="?action=list&sort=volume&dir= <?= $sortBy==='volume' && $sortDir==='ASC' ? 'DESC' : 'ASC' ?>&search=<?= urlencode($search) ?>&exchange=<?= urlencode($exchange) ?>">Volume</a></th>
                <th class="r"><a href="?action=list&sort=change_pct&dir=<?= $sortBy==='change_pct' && $sortDir==='ASC' ? 'DESC' : 'ASC' ?>&search=<?= urlencode($search) ?>&exchange=<?= urlencode($exchange) ?>">Change</a></th>
                <th class="r">Last Date</th>
            </tr>
        </thead>
        <tbody>
        <?php if (empty($symbols)): ?>
            <tr><td colspan="8" class="c text-muted" style="padding:40px">No symbols found</td></tr>
        <?php else: ?>
        <?php foreach ($symbols as $s): ?>
            <tr>
                <td><strong><a href="?action=detail&symbol=<?= urlencode($s['symbol']) ?>"><?= htmlspecialchars($s['symbol']) ?></a></strong></td>
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
</div>

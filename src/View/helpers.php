<?php
/**
 * View helpers — formatting functions for templates.
 */

function fmt_price($price) {
    if ($price === null) return '<span class="text-muted">N/A</span>';
    $color = '';
    if (func_num_args() > 1) {
        $prev = func_get_arg(1);
        if ($prev !== null && $prev != 0) {
            $change = (($price - $prev) / $prev) * 100;
            $color = $change > 0 ? ' style="color:#22c55e"' : ($change < 0 ? ' style="color:#ef4444"' : '');
        }
    }
    return '<span' . $color . '>$' . number_format((float)$price, 2) . '</span>';
}

function fmt_pct($val, $decimals = 2) {
    if ($val === null) return '<span class="text-muted">N/A</span>';
    $color = $val > 0 ? '#22c55e' : ($val < 0 ? '#ef4444' : '#6b7280');
    $sign = $val > 0 ? '+' : '';
    return '<span style="color:' . $color . '">' . $sign . number_format($val, $decimals) . '%</span>';
}

function fmt_num($val) {
    if ($val === null) return 'N/A';
    if (abs($val) >= 1_000_000_000) return number_format($val / 1_000_000_000, 2) . 'B';
    if (abs($val) >= 1_000_000) return number_format($val / 1_000_000, 2) . 'M';
    if (abs($val) >= 1_000) return number_format($val / 1_000, 1) . 'K';
    return number_format($val);
}

function fmt_date($date) {
    if ($date === null) return 'N/A';
    return htmlspecialchars(substr($date, 0, 10));
}

function active_class($page, $current) {
    return $page === $current ? 'active' : '';
}

function json_encode_safe($val) {
    return htmlspecialchars(json_encode($val, JSON_NUMERIC_CHECK));
}

function pageLink(int $target, string $baseQs, int $currentPage): string {
    if ($target < 1) return '#';
    $qs = $baseQs . '&page=' . $target;
    return '?' . ltrim($qs, '&');
}

function pageLinkList(int $target, string $baseQs, int $currentPage): string {
    return pageLink($target, $baseQs, $currentPage);
}

/**
 * Render a pagination toolbar: per-page DDL, "Showing X-Y of Z", Prev/Next.
 * Intended to be called from list/admin templates.
 */
function render_pagination(array $ctx): void
{
    $page       = (int)($ctx['page'] ?? 1);
    $perPage    = (int)($ctx['per_page'] ?? 50);
    $totalAll   = (int)($ctx['total_all'] ?? 0);
    $totalPages = (int)($ctx['total_pages'] ?? 1);

    $start = ($page - 1) * $perPage + 1;
    $end   = min($page * $perPage, $totalAll);

    $action     = $ctx['action'] ?? 'list';
    $search     = $ctx['search'] ?? '';
    $exchange   = $ctx['exchange'] ?? ($ctx['filter'] ?? '');
    $sortBy     = $ctx['sort'] ?? ($ctx['sortBy'] ?? 'symbol');
    $sortDir    = $ctx['dir']  ?? ($ctx['sortDir'] ?? 'ASC');
    $perPageOpts = $ctx['per_page_options'] ?? [50, 100, 250, 500, 1000];

    $params = [
        'action'   => $action,
        'search'   => $search,
        'exchange' => $exchange,
        'sort'     => $sortBy,
        'dir'      => $sortDir,
    ];
    if ($action === 'admin_symbols') {
        $params['filter'] = $ctx['filter'] ?? 'all';
    }
    $baseQs = trim(preg_replace('/&?page=\d+/', '', http_build_query($params)), '&');

    $pageLink = function (int $target) use ($baseQs): string {
        if ($target < 1) return '#';
        $qs = $baseQs ? $baseQs . '&page=' . $target : 'page=' . $target;
        return '?' . $qs;
    };

    $prevDisabled = $page <= 1 ? 'opacity:0.4;pointer-events:none;' : '';
    $nextDisabled = $page >= $totalPages ? 'opacity:0.4;pointer-events:none;' : '';
    ?>
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <form method="GET" style="display:inline-flex; align-items:center; gap:6px; font-size:0.85em;">
            <input type="hidden" name="action" value="<?= htmlspecialchars($action) ?>">
            <?php if ($action === 'admin_symbols'): ?>
                <input type="hidden" name="filter" value="<?= htmlspecialchars($ctx['filter'] ?? 'all') ?>">
            <?php endif; ?>
            <?php if ($search !== ''): ?>
                <input type="hidden" name="search" value="<?= htmlspecialchars($search) ?>">
            <?php endif; ?>
            <?php if ($exchange !== ''): ?>
                <input type="hidden" name="exchange" value="<?= htmlspecialchars($exchange) ?>">
            <?php endif; ?>
            <input type="hidden" name="sort" value="<?= htmlspecialchars($sortBy) ?>">
            <input type="hidden" name="dir" value="<?= htmlspecialchars($sortDir) ?>">
            <input type="hidden" name="page" value="1">
            <label>Show</label>
            <select name="per_page" onchange="this.form.submit()">
                <?php foreach ($perPageOpts as $opt): ?>
                    <option value="<?= $opt ?>" <?= $perPage === $opt ? 'selected' : '' ?>><?= $opt ?></option>
                <?php endforeach; ?>
            </select>
            <span class="muted">per page</span>
        </form>

        <div style="display:flex; align-items:center; gap:8px; font-size:0.85em;">
            <span class="muted">Showing <?= $start ?>–<?= $end ?> of <?= $totalAll ?></span>
            <a href="<?= $pageLink($page - 1) ?>" class="btn btn-sm" style="<?= $prevDisabled ?>">◀ Prev</a>
            <span style="color:var(--text2);">Page <?= $page ?> / <?= $totalPages ?></span>
            <a href="<?= $pageLink($page + 1) ?>" class="btn btn-sm" style="<?= $nextDisabled ?>">Next ▶</a>
        </div>
    </div>
    <?php
}

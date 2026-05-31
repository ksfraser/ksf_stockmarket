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

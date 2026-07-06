<?php
function fmt_large_num($val) {
    if ($val === null) return '—';
    $val = (float)$val;
    if (abs($val) >= 1e12) return number_format($val / 1e12, 2) . 'T';
    if (abs($val) >= 1e9) return number_format($val / 1e9, 2) . 'B';
    if (abs($val) >= 1e6) return number_format($val / 1e6, 1) . 'M';
    return number_format($val, 0);
}

<?php
// Backward-compat shim: the canonical helper functions (e.g. fmt_large_num)
// live in partials/detail/helpers.php. Requiring this file pulls them in
// without redefining anything (require_once guards against double-load).
require_once __DIR__ . '/detail/helpers.php';

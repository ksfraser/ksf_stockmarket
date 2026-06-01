<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?php echo htmlspecialchars($pageTitle); ?> — OWL Investment Dashboard</title>
<?php require __DIR__ . '/css.php'; ?>
</head>
<body>

<div class="nav">
    <span class="nav-brand">&#x1F989; OWL Investment</span>
    <a href="?action=overview" class="<?php echo active_class('overview', $action); ?>">Dashboard</a>
    <?php if (!empty($data['current_user'])): ?>
        <a href="?action=my_dashboard" class="<?php echo active_class('my_dashboard', $action); ?>">My Dashboard</a>
    <?php endif; ?>
    <a href="?action=portfolio" class="<?php echo active_class('portfolio', $action); ?>">Portfolio</a>
    <a href="?action=transactions" class="<?php echo active_class('transactions', $action); ?>">Transactions</a>
    <a href="?action=list" class="<?php echo active_class('list', $action); ?>">All Symbols</a>
    <a href="?action=strategy_stock" class="<?php echo active_class('strategy_stock', $action); ?>">Strategies</a>
    <a href="?action=admin_symbols" class="<?php echo active_class('admin_symbols', $action); ?>">Admin</a>
    <span class="right">
        <?php if (!empty($data['current_user'])): ?>
            <a href="?action=settings" style="font-size:0.85em;">&#x2699;&#xFE0F; <?php echo htmlspecialchars($data['current_user']['username']); ?></a>
            &nbsp;|&nbsp;
            <a href="?action=logout" style="font-size:0.85em;">Logout</a>
        <?php else: ?>
            <a href="?action=login" style="font-size:0.85em;">Login</a>
        <?php endif; ?>
        &nbsp;&mdash;&nbsp;
        Data: <?php echo htmlspecialchars($data['last_update'] ?? 'unknown'); ?>
    </span>
</div>

<div class="container">
<?php
$tplFile = __DIR__ . '/' . $template . '.php';
if (file_exists($tplFile)) {
    include $tplFile;
} else {
    echo '<div class="card"><em>Template not found: ' . htmlspecialchars($template) . '</em></div>';
}
?>
</div>

<?php
if (in_array($action ?? '', ['detail', 'indicators'])) {
    echo '<script src="/stockmarket/js/enhanced_charts.js?v=3"></script>';
}
require __DIR__ . '/js.php';
?>
</body>
</html>

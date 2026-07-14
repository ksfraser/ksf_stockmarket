<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?php echo htmlspecialchars($pageTitle); ?> — OWL Investment Dashboard</title>
<?php require __DIR__ . '/css.php'; ?>
<style>
.nav-system { background:var(--bg); border-bottom:1px solid var(--border); padding:6px 0; }
.nav-personal { background:var(--bg); border-bottom:1px solid var(--border); padding:6px 0; }
.nav-system a, .nav-personal a { color:var(--text3); text-decoration:none; padding:6px 12px; margin-right:4px; border-radius:4px; font-size:0.9em; transition:all 0.2s; }
.nav-system a:hover, .nav-personal a:hover { background:rgba(255,255,255,0.05); color:var(--text); }
.nav-system a.active, .nav-personal a.active { background:var(--accent); color:#fff; }
.nav-section { display:inline-block; margin-right:24px; }
.nav-section-label { font-size:0.7em; color:var(--text3); text-transform:uppercase; letter-spacing:0.5px; margin-right:8px; vertical-align:middle; }
.sort-link { color:var(--text); text-decoration:none; }
.sort-link:hover { text-decoration:underline; opacity:0.85; }
</style>
</head>
<body>

<div class="nav">
    <span class="nav-brand">&#x1F989; OWL Investment</span>
    
    <!-- System Navigation (available to all) -->
    <span class="nav-system">
        <span class="nav-section-label">System</span>
        <a href="?action=overview" class="<?php echo active_class('overview', $action); ?>">Dashboard</a>
        <a href="?action=list" class="<?php echo active_class('list', $action); ?>">All Symbols</a>
        <a href="?action=screener" class="<?php echo active_class('screener', $action); ?>">Screener</a>
        <a href="?action=strategy_stock" class="<?php echo active_class('strategy_stock', $action); ?>">Strategies</a>
        <a href="?action=advisor_backtest" class="<?php echo active_class('advisor_backtest', $action); ?>">Advisor Backtest</a>
        <a href="?action=seg_funds" class="<?php echo in_array($action, ['seg_funds','seg_fund_detail']) ? 'active' : ''; ?>">Seg Funds</a>
    </span>
    
    <?php if (!empty($data['current_user'])): ?>
    <!-- Personal Navigation (logged-in users) -->
    <span class="nav-personal" style="float:right;">
        <span class="nav-section-label">Personal</span>
        <a href="?action=my_dashboard" class="<?php echo active_class('my_dashboard', $action); ?>">My Dashboard</a>
        <a href="?action=portfolio" class="<?php echo active_class('portfolio', $action); ?>">Portfolio</a>
        <a href="?action=stop_orders" class="<?php echo active_class('stop_orders', $action); ?>">Stop Orders</a>
        <a href="?action=broker_stops" class="<?php echo active_class('broker_stops', $action); ?>">Broker Stops</a>
        <a href="?action=transactions" class="<?php echo active_class('transactions', $action); ?>">Transactions</a>
        <a href="?action=shared_with_me" class="<?php echo active_class('shared_with_me', $action); ?>">Shared with Me</a>
        <a href="?action=alerts_status" class="<?php echo active_class('alerts_status', $action); ?>">&#x1F4E3; Alerts</a>
        <a href="?action=upload" class="<?php echo active_class('upload', $action); ?>">&#x1F4E4; Upload</a>
        <a href="?action=export" class="<?php echo active_class('export', $action); ?>">&#x1F4BE; Export</a>
    </span>
    <div style="clear:both;"></div>
    <?php endif; ?>
    
    <span class="right">
        <?php if (!empty($data['current_user'])): ?>
            <a href="?action=settings" style="font-size:0.85em;">&#x2699;&#xFE0F; <?php echo htmlspecialchars($data['current_user']['username']); ?></a>
            &nbsp;|&nbsp;
            <a href="?action=logout" style="font-size:0.85em;">Logout</a>
            <?php if (($data['current_user']['role'] ?? '') === 'admin'): ?>
                |&nbsp;
                <a href="?action=admin_symbols" class="<?php echo active_class('admin_symbols', $action); ?>">Admin</a>
                <a href="?action=manual_ohlcv" class="<?php echo active_class('manual_ohlcv', $action); ?>">OHLCV Import</a>
                <a href="?action=admin_settings" class="<?php echo active_class('admin_settings', $action); ?>">Settings</a>
            <?php endif; ?>
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
require __DIR__ . '/js.php';
if (in_array($action ?? '', ['detail', 'indicators'])) {
    echo '<script src="/stockmarket/js/enhanced_charts.js?v=3"></script>';
}
?>
</body>
</html>
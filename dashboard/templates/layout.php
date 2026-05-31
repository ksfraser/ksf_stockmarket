<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= htmlspecialchars($pageTitle) ?> — OWL Investment Dashboard</title>
<?php include __DIR__ . '/css.php'; ?>
</head>
<body>

<div class="nav">
    <span class="nav-brand">&#x1F989; OWL Investment</span>
    <a href="?action=overview" class="<?= active_class('overview', $action) ?>">Dashboard</a>
    <a href="?action=portfolio" class="<?= active_class('portfolio', $action) ?>">Portfolio</a>
    <a href="?action=list" class="<?= active_class('list', $action) ?>">All Symbols</a>
    <span class="right">Data: <?= htmlspecialchars($data['last_update'] ?? 'unknown') ?></span>
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

<?php include __DIR__ . '/js.php'; ?>
</body>
</html>

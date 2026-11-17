<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= htmlspecialchars($pageTitle) ?> — OWL Investment Dashboard</title>
<?php require __DIR__ . '/../templates/css.php'; ?>
</head>
<body>

<div class="nav">
    <span class="nav-brand">&#x1F989; OWL Investment</span>
    <a href="/stockmarket/">Dashboard</a>
    <a href="/stockmarket/?action=portfolio">Portfolio</a>
    <a href="/stockmarket/?action=list">All Symbols</a>
    <a href="/stockmarket/?action=detail&symbol=<?= urlencode($symbol) ?>" class="active"><?= htmlspecialchars($symbol) ?></a>
</div>

<div class="container">
<?= $html ?>
</div>

<?php 
// Include enhanced charts JS for detail pages
if ($action === 'detail' || $action === 'indicators') {
    echo '<script src="/stockmarket/js/enhanced_charts.js"></script>';
}
require __DIR__ . '/../templates/js.php'; 
?>
</body>
</html>

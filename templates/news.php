<?php
/**
 * Financial News page - displays RSS news from Yahoo, MarketWatch, CNBC, CoinDesk.
 */
$news = $data['news'] ?? [];
$category = $data['category'] ?? 'stocks';
?>

<div class="card">
    <div class="card-header">📰 Financial News</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:12px;">Latest headlines from Yahoo Finance, MarketWatch, CNBC, CoinDesk, and CoinTelegraph.</p>
    
    <div style="display:flex;gap:8px;margin-bottom:12px;">
        <a href="?action=news&category=stocks" class="btn <?php echo $category === 'stocks' ? 'btn-primary' : ''; ?>" style="padding:4px 12px;font-size:0.85em;">Stocks</a>
        <a href="?action=news&category=crypto" class="btn <?php echo $category === 'crypto' ? 'btn-primary' : ''; ?>" style="padding:4px 12px;font-size:0.85em;">Crypto</a>
        <a href="?action=news&category=all" class="btn <?php echo $category === 'all' ? 'btn-primary' : ''; ?>" style="padding:4px 12px;font-size:0.85em;">All</a>
    </div>
    
    <?php if (empty($news)): ?>
        <p class="text-muted">No news items found. News is fetched daily during the nightly pipeline.</p>
    <?php else: ?>
        <div style="display:flex;flex-direction:column;gap:12px;">
            <?php foreach ($news as $n): ?>
                <div style="padding:12px;border:1px solid var(--border);border-radius:6px;background:var(--bg2);">
                    <div style="font-weight:600;margin-bottom:4px;">
                        <a href="<?php echo htmlspecialchars($n['url']); ?>" target="_blank" style="color:var(--accent);text-decoration:none;"><?php echo htmlspecialchars($n['title']); ?></a>
                    </div>
                    <div style="font-size:0.8em;color:var(--text3);margin-bottom:4px;">
                        <?php echo htmlspecialchars($n['source'] ?? ''); ?> • <?php echo htmlspecialchars($n['published'] ?? ''); ?>
                    </div>
                    <?php if (!empty($n['summary'])): ?>
                        <div style="font-size:0.85em;color:var(--text);"><?php echo htmlspecialchars($n['summary']); ?></div>
                    <?php endif; ?>
                </div>
            <?php endforeach; ?>
        </div>
    <?php endif; ?>
</div>
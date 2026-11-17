<?php
/**
 * Advisors & Portfolios — unified dashboard.
 * Data:
 *   $advisors — all available advisor_accounts
 *   $hired — map of advisor_id => user_advisors row for current user
 *   $screens — list of user_screens
 *   $strategies_by_sleeve — stock selection strategies grouped by sleeve
 *   $money_strategies — money management strategies
 */
$advisors = $data['advisors'] ?? [];
$hired = $data['hired'] ?? [];
$screens = $data['screens'] ?? [];
$strategiesBySleeve = $data['strategies_by_sleeve'] ?? [];
$moneyStrategies = $data['money_strategies'] ?? [];
?>
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">
        <h3>Advisors & Portfolios</h3>
        <span class="text-muted">Screens, strategies, advisors, and portfolio allocation in one place.</span>
    </div>
</div>

<!-- Screens Section -->
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">
        <h3>📊 Screens</h3>
        <a href="?action=create_rw_screen" class="btn" style="float:right;background:var(--accent);color:#fff;padding:6px 12px;border-radius:4px;text-decoration:none;font-size:0.85em;">+ Create Screen</a>
    </div>
    <div class="card-body">
        <p style="color:var(--text3);font-size:0.85em;margin-bottom:12px;">
            <?= count($screens); ?> screen(s) available.
            <a href="?action=rw_screens" style="color:var(--accent);">View all</a> |
            <a href="?action=screener" style="color:var(--accent);">TradingView Screener</a>
        </p>
        <?php if (!$screens): ?>
            <p class="text-muted">No screens yet. <a href="?action=create_rw_screen">Create your first screen</a>.</p>
        <?php else: ?>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Owner</th>
                            <th>Category</th>
                            <th>Updated</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach (array_slice($screens, 0, 10) as $s): ?>
                            <tr>
                                <td><?= htmlspecialchars($s['name']); ?></td>
                                <td><?= htmlspecialchars($s['owner'] ?? ''); ?></td>
                                <td><?= htmlspecialchars($s['category'] ?? '—'); ?></td>
                                <td><?= htmlspecialchars($s['updated_at'] ?? ''); ?></td>
                                <td>
                                    <a href="?action=run_rw_screen&id=<?= (int)$s['id']; ?>" class="btn btn-sm">Run</a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
</div>

<!-- Advisors Section -->
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">
        <h3>🧠 Advisors</h3>
    </div>
    <div class="card-body">
        <p style="color:var(--text3);font-size:0.85em;margin-bottom:12px;">
            <?= count($advisors); ?> advisor(s) available. Hired: <?= count($hired); ?>.
            <a href="?action=hire_advisors" style="color:var(--accent);">Manage advisors</a>
        </p>
        <?php if (!$advisors): ?>
            <p class="text-muted">No advisors configured yet.</p>
        <?php else: ?>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Advisor</th>
                            <th>Strategy</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($advisors as $a): ?>
                            <?php $my = $hired[(int)$a['id']] ?? null; ?>
                            <tr>
                                <td><strong><?= htmlspecialchars($a['display_name']); ?></strong></td>
                                <td><?= htmlspecialchars($a['strategy'] ?? ''); ?></td>
                                <td>
                                    <?php if ($my): ?>
                                        <?php if ($my['is_active']): ?>
                                            <span style="color:var(--green);">Active</span>
                                        <?php else: ?>
                                            <span style="color:var(--orange);">Paused</span>
                                        <?php endif; ?>
                                    <?php else: ?>
                                        <span style="color:var(--text3);">Not hired</span>
                                    <?php endif; ?>
                                </td>
                                <td>
                                    <a href="?action=hire_advisors" class="btn btn-sm"><?= $my ? 'Manage' : 'Hire'; ?></a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
</div>

<!-- Strategies Section -->
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">
        <h3>🎯 Strategies</h3>
    </div>
    <div class="card-body">
        <p style="color:var(--text3);font-size:0.85em;margin-bottom:12px;">
            Stock selection strategies (entry rules) and money/risk management rules.
            <a href="?action=strategy_stock" style="color:var(--accent);">Stock selection</a> |
            <a href="?action=strategy_money" style="color:var(--accent);">Money management</a> |
            <a href="?action=strategy_timing" style="color:var(--accent);">Timing</a>
        </p>
        <?php if (empty($strategiesBySleeve) && empty($moneyStrategies)): ?>
            <p class="text-muted">No strategies registered.</p>
        <?php else: ?>
            <?php foreach ($strategiesBySleeve as $sleeve => $strats): ?>
                <h4 style="margin-top:16px;text-transform:capitalize;"><?= htmlspecialchars($sleeve); ?></h4>
                <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
                    <?php foreach ($strats as $s): ?>
                        <span class="badge"><?= htmlspecialchars($s['name']); ?></span>
                    <?php endforeach; ?>
                </div>
            <?php endforeach; ?>
            <?php if (!empty($moneyStrategies)): ?>
                <h4 style="margin-top:16px;">Money & Risk Management</h4>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    <?php foreach ($moneyStrategies as $s): ?>
                        <span class="badge"><?= htmlspecialchars($s['name']); ?></span>
                    <?php endforeach; ?>
                </div>
            <?php endif; ?>
        <?php endif; ?>
    </div>
</div>

<!-- Portfolios Section -->
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">
        <h3>💼 Portfolios</h3>
    </div>
    <div class="card-body">
        <p style="color:var(--text3);font-size:0.85em;margin-bottom:12px;">
            View your own portfolio or shared advisor portfolios.
            <a href="?action=portfolio" style="color:var(--accent);">My portfolio</a> |
            <a href="?action=shared_with_me" style="color:var(--accent);">Shared with me</a>
        </p>
        <p class="text-muted">
            Advisor portfolios are generated when you hire an advisor and run their linked screens.
            Results are stored in <code>tradingview_screener_results</code> and positions in <code>layer3_portfolios</code>.
        </p>
    </div>
</div>

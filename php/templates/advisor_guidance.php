<?php
require_once __DIR__ . '/partials/helpers.php';

$strategies = [
    'buffett_quality' => [
        'name' => 'Buffett Quality',
        'icon' => '🇺🇸',
        'tagline' => 'Buy wonderful companies at fair prices.',
        'approach' => 'Looks for high-ROE, low-debt, consistent earnings companies with wide economic moats. Uses long-term compounding with minimal turnover.',
        'when_to_use' => 'Bull markets and secular growth trends. Best for patient capital with low turnover.',
        'risk' => 'Medium. Can underperform in rapid rotations or value-crunch regimes.',
    ],
    'dividend_growth' => [
        'name' => 'Dividend Growth',
        'icon' => '💵',
        'tagline' => 'Reinvest growing income streams.',
        'approach' => 'Targets companies with multi-year dividend growth, sustainable payout ratios, and rising free cash flow.',
        'when_to_use' => 'Rising-rate or inflationary environments where current income matters.',
        'risk' => 'Medium-low. Dividend cuts are the main risk; screen for payout < 70% and FCF coverage.',
    ],
    'momentum' => [
        'name' => 'Momentum',
        'icon' => '🚀',
        'tagline' => 'Ride the trend while it lasts.',
        'approach' => 'Buys securities showing strong relative strength and positive fundamentals acceleration. Cuts losers quickly.',
        'when_to_use' => 'Strong trending markets; avoid in choppy, range-bound conditions.',
        'risk' => 'High. Momentum crashes when leadership rotates. Use with stop-loss discipline.',
    ],
    'sector' => [
        'name' => 'Sector Rotation',
        'icon' => '🔄',
        'tagline' => 'Get in the right part of the boat.',
        'approach' => 'Weights sectors based on relative performance and macro regime (early/mid/late cycle). Reduces exposure to lagging sectors.',
        'when_to_use' => 'Macro-driven regime changes; ETF-heavy portfolios benefit most.',
        'risk' => 'Medium. Over-rotation can increase turnover and transaction costs.',
    ],
    'bond_basket' => [
        'name' => 'Bond Basket',
        'icon' => '🏦',
        'tagline' => 'Capture yield with lower volatility.',
        'approach' => 'Diversified fixed-income exposure across government, investment-grade corporate, and sometimes high-yield based on duration and credit quality.',
        'when_to_use' => 'Portfolio stabilization; equity drawdowns; liability-matching.',
        'risk' => 'Low-medium. Interest-rate and credit-spread risk remain.',
    ],
    'balanced_fund' => [
        'name' => 'Balanced Fund',
        'icon' => '⚖️',
        'tagline' => 'Mix growth and defense.',
        'approach' => 'Target allocation between equities and fixed income, rebalanced on schedule. Goal: smoothed returns with controlled drawdown.',
        'when_to_use' => 'Core holding; hands-off investors; moderate risk tolerance.',
        'risk' => 'Low-medium. Drawdowns still occur but are dampened by the fixed-income sleeve.',
    ],
    'vectorvest_safe' => [
        'name' => 'VectorVest Safe Stock',
        'icon' => '🛡️',
        'tagline' => 'Quality names with ownership and timing alignment.',
        'approach' => 'Combines fundamentals (ownership, earnings) with technical timing in a constrained universe of large-cap names.',
        'when_to_use' => 'Volatile or uncertain markets when absolute return matters more than benchmark beating.',
        'risk' => 'Medium. Concentrated names can lag high-momentum segments.',
    ],
];
?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">🎓 Advisor Guidance — Choosing Your Approach</div>
    <p class="muted">
        Each advisor follows a distinct market philosophy. You can hire multiple advisors;
        their trades will appear in your transactions with clear notes and rationale.
    </p>

    <div class="grid-2">
    <?php foreach ($strategies as $key => $s): ?>
        <div style="padding:16px;background:rgba(0,0,0,0.15);border-radius:var(--radius);border:1px solid var(--border);">
            <div style="font-size:1.6em;margin-bottom:8px;"><?= $s['icon'] ?></div>
            <strong style="font-size:1.05em;"><?= htmlspecialchars($s['name']) ?></strong>
            <br><small class="muted"><?= htmlspecialchars($key) ?></small>
            <p style="margin-top:8px;font-style:italic;color:var(--accent);">"<?= htmlspecialchars($s['tagline']) ?>"</p>
            <p style="margin-top:8px;font-size:0.92em;color:var(--text2);">
                <strong>Approach:</strong> <?= htmlspecialchars($s['approach']) ?>
            </p>
            <p style="margin-top:6px;font-size:0.92em;color:var(--text2);">
                <strong>When to use:</strong> <?= htmlspecialchars($s['when_to_use']) ?>
            </p>
            <p style="margin-top:6px;font-size:0.92em;color:var(--text2);">
                <strong>Risk:</strong> <?= htmlspecialchars($s['risk']) ?>
            </p>
        </div>
    <?php endforeach; ?>
    </div>
</div>

<div class="card" style="margin-top:24px;">
    <div class="card-header">📋 How Hiring Works</div>
    <div style="padding:8px 0;">
        <p><strong>1. Browse advisors</strong> — Each advisor has a philosophy, risk profile, and ideal market regime.</p>
        <p><strong>2. Hire</strong> — Adds them to your <em>My Advisors</em> list. The advisor cron can act on their behalf.</p>
        <p><strong>3. Transactions get notes</strong> — Every BUY/SELL written by an advisor includes transaction notes
            such as action, confidence, rank, and trigger reason. You can see this in the Transactions page.</p>
        <p><strong>4. Pause / Fire</strong> — Stop advisor activity without losing history. Firing removes them from your list.</p>
        <p><strong>5. Mix advisors</strong> — Hiring multiple advisors can diversify styles; compare their backtests in
            <a href="?action=advisor_backtest">Advisor Backtest Performance</a>.
        </p>
    </div>

<?php include __DIR__ . '/partials/atr_methodology.php'; ?>

<div style="margin-top:16px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center;">
    <a class="btn" href="?action=hire_advisors">Go to Advisor Marketplace</a>
    <a class="btn" href="?action=my_advisors" style="background:var(--bg2);color:var(--text);">My Advisors</a>
    <a class="btn" href="?action=knowledge_base" style="background:var(--bg2);color:var(--text);">📚 Knowledge Base</a>
</div>

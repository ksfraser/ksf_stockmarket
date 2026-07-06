<div class="card" style="margin-top:12px;">
    <div class="card-header">Fundamentals Deep Dive</div>
    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; font-size:0.9em;">
        <div><span class="text-muted">Forward P/E</span><br><strong><?= $fundamentals['forward_pe'] ? number_format($fundamentals['forward_pe'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Price/Book</span><br><strong><?= $fundamentals['price_to_book'] ? number_format($fundamentals['price_to_book'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Price/Sales</span><br><strong><?= $fundamentals['price_to_sales'] ? number_format($fundamentals['price_to_sales'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Book Value</span><br><strong><?= $fundamentals['book_value'] ? '$' . number_format($fundamentals['book_value'], 2) : '—' ?></strong></div>
        <div><span class="text-muted">Free Cash Flow</span><br><strong><?= fmt_large_num($fundamentals['free_cash_flow'] ?? null) ?></strong></div>
        <div><span class="text-muted">Operating CF</span><br><strong><?= fmt_large_num($fundamentals['operating_cash_flow'] ?? null) ?></strong></div>
        <div><span class="text-muted">Revenue</span><br><strong><?= fmt_large_num($fundamentals['total_revenue'] ?? null) ?></strong></div>
        <div><span class="text-muted">Revenue Growth</span><br><strong style="color:<?= ($fundamentals['revenue_growth'] ?? 0) > 0 ? 'var(--green)' : 'var(--red)' ?>"><?= $fundamentals['revenue_growth'] ? number_format($fundamentals['revenue_growth'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">Gross Margin</span><br><strong><?= $fundamentals['gross_margin'] ? number_format($fundamentals['gross_margin'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">Operating Margin</span><br><strong><?= $fundamentals['operating_margin'] ? number_format($fundamentals['operating_margin'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">ROA</span><br><strong><?= $fundamentals['roa'] ? number_format($fundamentals['roa'], 1) . '%' : '—' ?></strong></div>
        <div><span class="text-muted">EV/EBITDA</span><br><strong><?= $fundamentals['enterprise_to_ebitda'] ? number_format($fundamentals['enterprise_to_ebitda'], 2) : '—' ?></strong></div>
    </div>
</div>

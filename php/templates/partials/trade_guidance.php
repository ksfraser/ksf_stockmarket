<div class="card" style="margin-bottom:16px; background:var(--bg2)">
    <div class="card-header" style="cursor:pointer" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
        📖 Trade Format & Guidance <span style="float:right">&#9660;</span>
    </div>
    <div style="padding:12px 16px; display:none">
        <p><strong>Recommended order format used by advisors:</strong></p>
        <pre style="background:var(--bg); padding:10px; border-radius:6px; overflow:auto">Buy 100 ABC at $12.00
Max: $12.45
Stop limit: $10.92
ATR stop (2.5x): $9.80</pre>
        <ul>
            <li><strong>Max</strong> — the most you’re willing to pay.</li>
            <li><strong>Stop limit</strong> — initial hard stop below entry.</li>
            <li><strong>ATR stop (2.5x)</strong> — trailing stop based on 14-day ATR × 2.5; move up as price rises.</li>
        </ul>
        <p style="color:var(--text3); font-size:0.9em">
            Auto-trading uses T+2 settlement: cash is reserved on trade day and actual movement happens 2 business days later.
        </p>
    </div>
</div>

<div style="margin-top:16px;padding:16px;background:rgba(0,0,0,0.15);border-radius:var(--radius);border:1px solid var(--border);">
    <strong style="font-size:1.1em;">📐 ATR Trailing-Stop Methodology</strong>
    <p style="margin-top:8px;">
        Every advisor exit uses an <strong>Average True Range (ATR)</strong> stop. ATR measures the
        typical daily dollar swing of a stock over a 14-day lookback. We use a simplified
        close-to-close version:
    </p>
    <pre style="background:rgba(0,0,0,0.35);padding:10px;border-radius:8px;overflow:auto;font-size:0.85em;">atr14 = average( |close_today − close_yesterday| )  over last 14 closes</pre>
    <p style="margin-top:10px;">
        The <strong>stop threshold</strong> is set at entry:
    </p>
    <pre style="background:rgba(0,0,0,0.35);padding:10px;border-radius:8px;overflow:auto;font-size:0.85em;">threshold = entry_price − (atr_multiplier × atr14)
exit when last_price ≤ threshold</pre>
    <p style="margin-top:10px;">
        Different strategies use different multipliers:
    </p>
    <table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:0.9em;">
        <tr style="border-bottom:1px solid var(--border);">
            <th style="text-align:left;padding:6px;">Strategy</th>
            <th style="text-align:center;padding:6px;">Default ATR×</th>
            <th style="text-align:left;padding:6px;">Effect</th>
        </tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:6px;">Buffett Quality</td>
            <td style="text-align:center;padding:6px;">2.5</td>
            <td style="padding:6px;">Tight → loose depending on conviction bucket</td>
        </tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:6px;">Momentum</td>
            <td style="text-align:center;padding:6px;">2.5</td>
            <td style="padding:6px;">Wide to ride volatile breakouts</td>
        </tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:6px;">Bond Basket / Balanced</td>
            <td style="text-align:center;padding:6px;">1.0</td>
            <td style="padding:6px;">Tight for low-vol assets</td>
        </tr>
        <tr>
            <td style="padding:6px;">Dividend / Sector</td>
            <td style="text-align:center;padding:6px;">0 (10% fixed)</td>
            <td style="padding:6px;">Simple percent stop when ATR is unreliable</td>
        </tr>
    </table>
    <p style="margin-top:12px;">
        <strong>Why 2×–2.5× ATR shows up as best in PnL:</strong> In normal market conditions,
        most daily price swings stay inside 1–2 ATRs. A <strong>2× ATR stop</strong> is near the
        boundary of routine pullbacks vs. genuine trend exhaustion—early enough to protect capital,
        but not so tight that you get stopped out by normal noise. A <strong>2.5× ATR stop</strong>
        gives even more room, letting winners run longer; you exit only when the move is clearly
        broken. Both cluster around the same PnL sweet spot because they filter out the same
        whipsaws while capturing most real reversals.
    </p>
    <p>
        <strong>Would 2.25× be better?</strong> We can’t say from current PnL data alone.
        If the distribution has two peaks (one at 2×, one at 2.5×), 2.25× might fall in between
        and be worse than both. If the bump is a flat plateau, 2.25× would be nearly identical
        to 2× and 2.5×. The only way to know is to run the backtest with <code>atr_multiplier=2.25</code>
        across the same universe and compare Sharpe / max-drawdown / PnL mode.
    </p>
</div>
<div style="margin-top:16px;padding:16px;background:rgba(0,0,0,0.15);border-radius:var(--radius);border:1px solid var(--border);">
    <strong style="font-size:1.1em;">🧠 Optional Knowledge-Base Rules</strong>
    <p style="margin-top:8px;">These are <strong>disabled by default</strong>. When enabled, they encode the
        Wealth Principles and Becoming Rich Is Simple knowledge base directly into advisor execution.
        They live in <code>strategy_rules.risk_rules.optional_rules</code> and validate trades before they reach position sizing.
    </p>
    <table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:0.9em;">
        <tr style="border-bottom:1px solid var(--border);">
            <th style="text-align:left;padding:6px;">Rule</th>
            <th style="text-align:center;padding:6px;">Key</th>
            <th style="text-align:left;padding:6px;">KB Source</th>
            <th style="text-align:left;padding:6px;">Behavior</th>
        </tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:6px;">Min reward:risk ratio</td>
            <td style="text-align:center;padding:6px;"><code>min_reward_risk_ratio</code></td>
            <td style="padding:6px;">Asymmetric risk-reward</td>
            <td style="padding:6px;">Require confidence ÷ effective_stop ≥ threshold. At 5, most momentum gets filtered.</td>
        </tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:6px;">Emergency buffer</td>
            <td style="text-align:center;padding:6px;"><code>emergency_buffer_pct</code></td>
            <td style="padding:6px;">Save first / emergency fund</td>
            <td style="padding:6px;">Block new entries when cash / total value falls below threshold.</td>
        </tr>
        <tr>
            <td style="padding:6px;">Asset blacklist</td>
            <td style="text-align:center;padding:6px;"><code>blacklist_asset_classes</code></td>
            <td style="padding:6px;">Avoid crypto, covered calls, thematic ETFs</td>
            <td style="padding:6px;">Skip symbols whose ticker/sector/subclass matches any item (e.g. <code>BTC</code>, <code>COVERED</code>).</td>
        </tr>
    </table>
</div>

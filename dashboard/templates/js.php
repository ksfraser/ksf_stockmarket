<script>
// ── Simple Canvas Chart (no external dependencies) ──

function drawPriceChart(canvasId, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.parentElement.clientWidth;
    const H = canvas.height = canvas.parentElement.clientHeight || 300;
    const pad = { top: 20, right: 60, bottom: 30, left: 10 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const prices = data.map(d => parseFloat(d.close));
    const volumes = data.map(d => parseFloat(d.volume || 0));
    const minP = Math.min(...prices) * 0.995;
    const maxP = Math.max(...prices) * 1.005;
    const minV = Math.min(...volumes);
    const maxV = Math.max(...volumes);

    function x(i) { return pad.left + (i / (data.length - 1)) * plotW; }
    function yp(p) { return pad.top + (1 - (p - minP) / (maxP - minP)) * plotH; }
    function yv(v) { return pad.top + plotH - ((v - minV) / (maxV - minV + 1)) * (plotH * 0.3); }

    // Background
    ctx.fillStyle = '#1a2744';
    ctx.fillRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = '#2d3f5f';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = pad.top + (i / 4) * plotH;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    }

    // Volume bars
    ctx.fillStyle = 'rgba(59, 130, 246, 0.15)';
    for (let i = 0; i < data.length; i++) {
        const bw = plotW / data.length;
        ctx.fillRect(x(i), yv(volumes[i]), bw - 1, pad.top + plotH - yv(volumes[i]));
    }

    // Price line
    ctx.beginPath();
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 1.5;
    for (let i = 0; i < prices.length; i++) {
        if (i === 0) ctx.moveTo(x(i), yp(prices[i]));
        else ctx.lineTo(x(i), yp(prices[i]));
    }
    ctx.stroke();

    // Gradient fill under line
    ctx.lineTo(x(prices.length - 1), pad.top + plotH);
    ctx.lineTo(x(0), pad.top + plotH);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
    grad.addColorStop(0, 'rgba(59, 130, 246, 0.2)');
    grad.addColorStop(1, 'rgba(59, 130, 246, 0)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Price labels
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px system-ui';
    ctx.textAlign = 'left';
    for (let i = 0; i <= 4; i++) {
        const p = minP + (1 - i / 4) * (maxP - minP);
        const y = pad.top + (i / 4) * plotH;
        ctx.fillText('$' + p.toFixed(2), W - pad.right + 5, y + 3);
    }

    // Date labels
    ctx.textAlign = 'center';
    const step = Math.ceil(data.length / 8);
    for (let i = 0; i < data.length; i += step) {
        ctx.fillText(data[i].price_date.slice(0, 10), x(i), H - 8);
    }

    // Crosshair on mousemove
    canvas.onmousemove = function(e) {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const idx = Math.round(((mx - pad.left) / plotW) * (data.length - 1));
        if (idx >= 0 && idx < data.length) {
            // Redraw
            drawPriceChart(canvasId, data, options);

            // Crosshair
            ctx.strokeStyle = '#64748b';
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(x(idx), pad.top); ctx.lineTo(x(idx), pad.top + plotH);
            ctx.stroke();
            ctx.setLineDash([]);

            // Label
            const p = prices[idx];
            ctx.fillStyle = '#3b82f6';
            ctx.fillRect(x(idx) - 30, yp(p) - 12, 60, 16);
            ctx.fillStyle = '#fff';
            ctx.font = '10px system-ui';
            ctx.textAlign = 'center';
            ctx.fillText('$' + p.toFixed(2), x(idx), yp(p) - 2);
        }
    };

    canvas.onmouseleave = function() {
        drawPriceChart(canvasId, data, options);
    };
}

function drawIndicatorChart(canvasId, data, key, color, minVal, maxVal) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.parentElement.clientWidth;
    const H = canvas.height = canvas.parentElement.clientHeight || 120;
    const pad = { top: 10, right: 10, bottom: 20, left: 10 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    const values = data.map(d => parseFloat(d[key])).filter(v => !isNaN(v));
    if (values.length < 2) return;

    const mn = minVal !== undefined ? minVal : Math.min(...values) * 0.99;
    const mx = maxVal !== undefined ? maxVal : Math.max(...values) * 1.01;

    ctx.fillStyle = '#1a2744';
    ctx.fillRect(0, 0, W, H);

    // Reference lines
    const refs = [];
    if (minVal === undefined && maxVal === undefined) {
        if (mn < 30 && mx > 70) refs.push([30, '#ef444433'], [50, '#64748b22'], [70, '#22c55e33']);
    }
    refs.forEach(([val, col]) => {
        const y = pad.top + (1 - (val - mn) / (mx - mn)) * plotH;
        ctx.strokeStyle = col;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
        ctx.setLineDash([]);
    });

    // Line
    ctx.beginPath();
    ctx.strokeStyle = color || '#eab308';
    ctx.lineWidth = 1.5;
    for (let i = 0; i < values.length; i++) {
        const px = pad.left + (i / (values.length - 1)) * plotW;
        const py = pad.top + (1 - (values[i] - mn) / (mx - mn)) * plotH;
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // Label
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px system-ui';
    ctx.textAlign = 'right';
    const last = values[values.length - 1];
    ctx.fillText(last.toFixed(2), W - pad.right, pad.top + 10);
}

// ── Initialize charts on page load ──
document.addEventListener('DOMContentLoaded', function() {
    // Charts with data-chart attribute
    document.querySelectorAll('[data-chart]').forEach(function(el) {
        try {
            const data = JSON.parse(el.dataset.chart);
            const type = el.dataset.type || 'price';
            if (type === 'price') drawPriceChart(el.id, data);
            else drawIndicatorChart(el.id, data, el.dataset.key, el.dataset.color, parseFloat(el.dataset.min), parseFloat(el.dataset.max));
        } catch (e) {}
    });
});

// ── Auto-refresh data status every 60s ──
setInterval(function() {
    const statusEl = document.getElementById('data-freshness');
    if (statusEl) {
        statusEl.style.opacity = '0.5';
    }
}, 60000);
</script>

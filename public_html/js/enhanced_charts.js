/**
 * Enhanced Canvas Charts for Symbol Detail Page
 * Draws: Entry/Stop lines, Analyst targets, News markers on price chart
 * Draws: RSI, MACD, Stochastic, ATR, Bollinger Band charts
 * Depends on: drawPriceChart() from js.php (loaded first)
 */

(function() {
    'use strict';

    // Wait for DOM and Chart data
    function init() {
        // Draw enhanced price chart if available
        if (typeof window.chartData !== 'undefined' && window.chartData.length) {
            if (typeof drawPriceChart !== 'undefined') {
                drawEnhancedPriceChart();
            }
        }
        // Draw oscillator charts independently (don't require price chart data)
        drawOscillatorCharts();
        drawVolatilityCharts();
    }

    function drawEnhancedPriceChart() {
        const canvas = document.getElementById('priceChart');
        if (!canvas) return;

        const data = window.chartData;
        const W = canvas.width = canvas.parentElement.clientWidth;
        const H = canvas.height = 400;
        const pad = { top: 20, right: 60, bottom: 30, left: 10 };
        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        const prices = data.map(d => d.close);
        const volumes = data.map(d => d.volume || 0);
        const dates = data.map(d => d.date);
        const minP = Math.min(...prices) * 0.98;
        const maxP = Math.max(...prices) * 1.02;
        const maxV = Math.max(...volumes);

        function x(i) { return pad.left + (i / (data.length - 1)) * plotW; }
        function yp(p) { return pad.top + (1 - (p - minP) / (maxP - minP)) * plotH; }
        function yv(v) { return pad.top + plotH - (v / (maxV + 1)) * (plotH * 0.25); }

        // Background
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#1a2744';
        ctx.fillRect(0, 0, W, H);

        // Grid
        ctx.strokeStyle = '#243656';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = pad.top + (i / 5) * plotH;
            ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
        }

        // Volume bars - color coded by price change (green=up, red=down) + volume average lines
        const volAvg22 = calculateVolumeAvg(volumes, 22);
        const volAvg63 = calculateVolumeAvg(volumes, 63);
        for (let i = 0; i < data.length; i++) {
            const priceChange = i > 0 ? data[i].close - data[i-1].close : 0;
            ctx.fillStyle = priceChange >= 0 ? 'rgba(76,175,80,0.6)' : 'rgba(244,67,54,0.6)';
            ctx.fillRect(x(i) - 1, yv(volumes[i]), 2, pad.top + plotH - yv(volumes[i]));
        }
        // 22-day volume average line (monthly)
        const yvAvg22 = yv(volAvg22);
        ctx.strokeStyle = 'rgba(255,193,7,0.7)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(pad.left, yvAvg22);
        ctx.lineTo(W - pad.right, yvAvg22);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(255,193,7,0.8)';
        ctx.font = '10px system-ui';
        ctx.textAlign = 'left';
        ctx.fillText('Vol Avg 22d: ' + (volAvg22/1e6).toFixed(1) + 'M', pad.left + 4, yvAvg22 - 4);
        // 63-day volume average line (quarterly)
        const yvAvg63 = yv(volAvg63);
        ctx.strokeStyle = 'rgba(156,39,176,0.7)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(pad.left, yvAvg63);
        ctx.lineTo(W - pad.right, yvAvg63);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(156,39,176,0.8)';
        ctx.font = '10px system-ui';
        ctx.textAlign = 'left';
        ctx.fillText('Vol Avg 63d: ' + (volAvg63/1e6).toFixed(1) + 'M', pad.left + 4, yvAvg63 - 4);

        // Price line
        ctx.beginPath();
        ctx.strokeStyle = '#4CAF50';
        ctx.lineWidth = 2;
        for (let i = 0; i < prices.length; i++) {
            if (i === 0) ctx.moveTo(x(i), yp(prices[i])); else ctx.lineTo(x(i), yp(prices[i]));
        }
        ctx.stroke();

        // ── OVERLAYS ──

        // Entry price line
        if (window.entryPrice && window.entryPrice > minP && window.entryPrice < maxP) {
            const ye = yp(window.entryPrice);
            ctx.strokeStyle = '#FF9800';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 3]);
            ctx.beginPath(); ctx.moveTo(pad.left, ye); ctx.lineTo(W - pad.right, ye); ctx.stroke();
            ctx.setLineDash([]);
            // Label
            ctx.fillStyle = '#FF9800';
            ctx.font = '11px system-ui';
            ctx.textAlign = 'left';
            ctx.fillText('Entry $' + window.entryPrice.toFixed(2), pad.left + 4, ye - 4);
        }

        // Trailing stop line
        if (window.stopPrice && window.stopPrice > minP && window.stopPrice < maxP) {
            const ys = yp(window.stopPrice);
            ctx.strokeStyle = '#f44336';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([6, 3]);
            ctx.beginPath(); ctx.moveTo(pad.left, ys); ctx.lineTo(W - pad.right, ys); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#f44336';
            ctx.font = '11px system-ui';
            ctx.textAlign = 'left';
            ctx.fillText('Stop $' + window.stopPrice.toFixed(2), pad.left + 4, ys + 12);
        }

        // Consensus target line
        if (window.consensusPrice && window.consensusPrice > minP && window.consensusPrice < maxP) {
            const yt = yp(window.consensusPrice);
            ctx.strokeStyle = '#9C27B0';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([10, 5]);
            ctx.beginPath(); ctx.moveTo(pad.left, yt); ctx.lineTo(W - pad.right, yt); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#9C27B0';
            ctx.font = '11px system-ui';
            ctx.textAlign = 'right';
            ctx.fillText('Consensus $' + window.consensusPrice.toFixed(2), W - pad.right - 4, yt - 4);
        }

        // Individual analyst targets (triangles)
        if (window.analystTargets && window.analystTargets.length) {
            window.analystTargets.forEach(function(t) {
                const idx = dates.indexOf(t.date);
                if (idx >= 0 && t.price >= minP && t.price <= maxP) {
                    const tx = x(idx);
                    const ty = yp(t.price);
                    // Triangle
                    ctx.fillStyle = '#FFC107';
                    ctx.beginPath();
                    ctx.moveTo(tx, ty - 8);
                    ctx.lineTo(tx - 5, ty + 4);
                    ctx.lineTo(tx + 5, ty + 4);
                    ctx.closePath();
                    ctx.fill();
                    // Label
                    ctx.fillStyle = '#FFC107';
                    ctx.font = '9px system-ui';
                    ctx.textAlign = 'center';
                    ctx.fillText((t.firm || '').substring(0, 8), tx, ty + 16);
                }
            });
        }

        // News markers (red dots on price line)
        if (window.newsMarkers && window.newsMarkers.length) {
            window.newsMarkers.forEach(function(n) {
                const idx = dates.findIndex(d => d === n.date || d.substring(0,10) === n.date.substring(0,10));
                if (idx >= 0) {
                    const nx = x(idx);
                    const ny = yp(prices[idx]);
                    ctx.fillStyle = '#f44336';
                    ctx.beginPath();
                    ctx.arc(nx, ny, 5, 0, Math.PI * 2);
                    ctx.fill();
                    // White border
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            });
        }

        // Price axis labels
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px system-ui';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const p = minP + (maxP - minP) * (1 - i / 5);
            ctx.fillText('$' + p.toFixed(0), W - pad.right + 4, pad.top + (i / 5) * plotH + 4);
        }

        // Date labels
        ctx.textAlign = 'center';
        const step = Math.ceil(dates.length / 8);
        for (let i = 0; i < dates.length; i += step) {
            ctx.fillText(dates[i].substring(5), x(i), H - 8);
        }
    }

    function drawOscillatorCharts() {
        // RSI
        if (window.rsiData && window.rsiData.length > 1) {
            drawLineChart('rsiChart', window.rsiData.map(d => d.value), '#9C27B0', 0, 100, [30, 50, 70]);
        }
        // MACD
        if (window.macdData && window.macdData.length > 1) {
            drawMACDChart('macdChart', window.macdData);
        }
        // Stochastic
        if (window.stochData && window.stochData.length > 1) {
            drawLineChart('stochChart', window.stochData.map(d => d.k), '#2196F3', 0, 100, [20, 50, 80], window.stochData.map(d => d.d));
        }
    }

    function drawVolatilityCharts() {
        if (window.atrData && window.atrData.length > 1) {
            drawLineChart('atrChart', window.atrData.map(d => d.atr), '#FF9800');
        }
        if (window.bbData && window.bbData.length > 1) {
            drawBBChart('bbChart', window.bbData);
        }
    }

    function drawLineChart(canvasId, values, color, minVal, maxVal, refLines, values2) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !values || values.length < 2) return;
        const ctx = canvas.getContext('2d');
        const W = canvas.width = canvas.parentElement.clientWidth;
        const H = canvas.height = canvas.parentElement.clientHeight || 180;
        const pad = { top: 15, right: 10, bottom: 20, left: 10 };
        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        const mn = minVal !== undefined ? minVal : Math.min(...values) * 0.99;
        const mx = maxVal !== undefined ? maxVal : Math.max(...values) * 1.01;

        ctx.fillStyle = '#1a2744';
        ctx.fillRect(0, 0, W, H);

        // Ref lines
        if (refLines) {
            refLines.forEach(function(v) {
                const y = pad.top + (1 - (v - mn) / (mx - mn)) * plotH;
                ctx.strokeStyle = v === 50 ? '#64748b33' : (v < 50 ? '#22c55e22' : '#ef444422');
                ctx.lineWidth = 1;
                ctx.setLineDash([2, 2]);
                ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
                ctx.setLineDash([]);
            });
        }

        // Main line
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        for (let i = 0; i < values.length; i++) {
            const px = pad.left + (i / (values.length - 1)) * plotW;
            const py = pad.top + (1 - (values[i] - mn) / (mx - mn)) * plotH;
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke();

        // Second line (e.g., Stochastic %D)
        if (values2 && values2.length === values.length) {
            ctx.beginPath();
            ctx.strokeStyle = '#FF9800';
            ctx.lineWidth = 1;
            for (let i = 0; i < values2.length; i++) {
                const px = pad.left + (i / (values2.length - 1)) * plotW;
                const py = pad.top + (1 - (values2[i] - mn) / (mx - mn)) * plotH;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();
        }

        // Current value label
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px system-ui';
        ctx.textAlign = 'right';
        ctx.fillText(values[values.length - 1].toFixed(2), W - pad.right, pad.top + 10);
    }

    function drawMACDChart(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !data || data.length < 2) return;
        const ctx = canvas.getContext('2d');
        const W = canvas.width = canvas.parentElement.clientWidth;
        const H = canvas.height = canvas.parentElement.clientHeight || 180;
        const pad = { top: 15, right: 10, bottom: 20, left: 10 };
        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        const macdVals = data.map(d => d.macd);
        const signalVals = data.map(d => d.signal);
        const histVals = macdVals.map((m, i) => m - signalVals[i]);
        const allVals = [...macdVals, ...signalVals, ...histVals];
        const mn = Math.min(...allVals) * 1.1;
        const mx = Math.max(...allVals) * 1.1;

        ctx.fillStyle = '#1a2744';
        ctx.fillRect(0, 0, W, H);

        // Zero line
        const y0 = pad.top + (1 - (0 - mn) / (mx - mn)) * plotH;
        ctx.strokeStyle = '#64748b33';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(pad.left, y0); ctx.lineTo(W - pad.right, y0); ctx.stroke();

        // Histogram
        for (let i = 0; i < histVals.length; i++) {
            const px = pad.left + (i / (histVals.length - 1)) * plotW;
            const yv = pad.top + (1 - (histVals[i] - mn) / (mx - mn)) * plotH;
            ctx.fillStyle = histVals[i] >= 0 ? 'rgba(76,175,80,0.3)' : 'rgba(244,67,54,0.3)';
            ctx.fillRect(px - 1, Math.min(y0, yv), 2, Math.abs(y0 - yv));
        }

        // MACD line
        ctx.beginPath(); ctx.strokeStyle = '#2196F3'; ctx.lineWidth = 1.5;
        for (let i = 0; i < macdVals.length; i++) {
            const px = pad.left + (i / (macdVals.length - 1)) * plotW;
            const py = pad.top + (1 - (macdVals[i] - mn) / (mx - mn)) * plotH;
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke();

        // Signal line
        ctx.beginPath(); ctx.strokeStyle = '#FF9800'; ctx.lineWidth = 1;
        for (let i = 0; i < signalVals.length; i++) {
            const px = pad.left + (i / (signalVals.length - 1)) * plotW;
            const py = pad.top + (1 - (signalVals[i] - mn) / (mx - mn)) * plotH;
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke();
    }

    function drawBBChart(canvasId, data) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !data || data.length < 2) return;
        const ctx = canvas.getContext('2d');
        const W = canvas.width = canvas.parentElement.clientWidth;
        const H = canvas.height = canvas.parentElement.clientHeight || 200;
        const pad = { top: 15, right: 50, bottom: 20, left: 10 };
        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        const allVals = data.flatMap(d => [d.upper, d.mid, d.lower]);
        const mn = Math.min(...allVals) * 0.995;
        const mx = Math.max(...allVals) * 1.005;

        ctx.fillStyle = '#1a2744';
        ctx.fillRect(0, 0, W, H);

        // Fill between upper and lower
        ctx.fillStyle = 'rgba(96,125,139,0.1)';
        ctx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const px = pad.left + (i / (data.length - 1)) * plotW;
            const py = pad.top + (1 - (data[i].upper - mn) / (mx - mn)) * plotH;
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        for (let i = data.length - 1; i >= 0; i--) {
            const px = pad.left + (i / (data.length - 1)) * plotW;
            const py = pad.top + (1 - (data[i].lower - mn) / (mx - mn)) * plotH;
            ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();

        // Lines
        function drawBand(values, color, dash) {
            ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 1.5;
            if (dash) ctx.setLineDash(dash);
            for (let i = 0; i < values.length; i++) {
                const px = pad.left + (i / (values.length - 1)) * plotW;
                const py = pad.top + (1 - (values[i] - mn) / (mx - mn)) * plotH;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke(); ctx.setLineDash([]);
        }
        drawBand(data.map(d => d.upper), '#f44336');
        drawBand(data.map(d => d.mid), '#607D8B', [4, 4]);
        drawBand(data.map(d => d.lower), '#4CAF50');

        // Labels
        ctx.fillStyle = '#94a3b8'; ctx.font = '10px system-ui'; ctx.textAlign = 'right';
        ctx.fillText('$' + mx.toFixed(0), W - pad.right + 4, pad.top + 10);
        ctx.fillText('$' + mn.toFixed(0), W - pad.right + 4, pad.top + plotH);
    }

    function calculateVolumeAvg(volumes, period) {
        if (volumes.length < period) return volumes.reduce((a, b) => a + b, 0) / volumes.length;
        const sum = volumes.slice(-period).reduce((a, b) => a + b, 0);
        return sum / period;
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
    --bg: #0f1729; --bg2: #1a2744; --bg3: #243656;
    --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
    --accent: #3b82f6; --accent2: #6366f1;
    --green: #22c55e; --red: #ef4444; --yellow: #eab308; --orange: #f97316;
    --border: #2d3f5f; --radius: 8px;
}
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Navigation ── */
.nav { background: var(--bg2); border-bottom: 1px solid var(--border); padding: 0 20px; display: flex; align-items: center; gap: 8px; height: 56px; }
.nav-brand { font-weight: 700; font-size: 1.1em; color: var(--accent); margin-right: 20px; }
.nav a { padding: 8px 14px; border-radius: var(--radius); color: var(--text2); font-size: 0.9em; }
.nav a:hover, .nav a.active { background: var(--bg3); color: var(--text); text-decoration: none; }
.nav .right { margin-left: auto; color: var(--text3); font-size: 0.85em; }

/* ── Container ── */
.container { max-width: 1400px; margin: 0 auto; padding: 24px 20px; }

/* ── Cards ── */
.card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; margin-bottom: 20px; }
.card-header { font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text3); margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }

/* ── Stats Grid ── */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.stat-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; text-align: center; }
.stat-value { font-size: 1.8em; font-weight: 700; }
.stat-label { font-size: 0.8em; color: var(--text3); margin-top: 4px; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
th { text-align: left; padding: 10px 12px; background: var(--bg3); color: var(--text2); font-weight: 600; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em; position: sticky; top: 0; }
td { padding: 9px 12px; border-bottom: 1px solid var(--border); }
tr:hover td { background: var(--bg2); }
.c { text-align: center; }
.r { text-align: right; }
.green { color: var(--green); }
.red { color: var(--red); }
.text-muted { color: var(--text3); }

/* ── Grid layouts ── */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }

/* ── Forms ── */
input[type="text"], select { background: var(--bg3); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: var(--radius); font-size: 0.9em; }
input[type="text"]:focus { outline: none; border-color: var(--accent); }
.btn { display: inline-block; padding: 8px 16px; background: var(--accent); color: #fff; border: none; border-radius: var(--radius); cursor: pointer; font-size: 0.88em; }
.btn:hover { background: var(--accent2); text-decoration: none; }
.btn-sm { padding: 4px 10px; font-size: 0.8em; }

/* ── Chart container ── */
.chart-container { position: relative; width: 100%; height: 300px; }
.chart-lg { height: 400px; }

/* ── Search bar ── */
.search-bar { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
.search-bar input { flex: 1; }

/* ── Indicator grid ── */
.ind-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.ind-item { background: var(--bg3); border-radius: var(--radius); padding: 12px; }
.ind-name { font-size: 0.75em; color: var(--text3); text-transform: uppercase; letter-spacing: 0.05em; }
.ind-value { font-size: 1.3em; font-weight: 600; margin-top: 4px; }

/* ── Bar ── */
.bar { height: 4px; background: var(--bg3); border-radius: 2px; margin-top: 6px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 2px; }

/* ── P and L colors ── */
.pnl-positive { color: var(--green); }
.pnl-negative { color: var(--red); }

/* ── Mini price spark ── */
.spark { display: inline-flex; align-items: flex-end; gap: 1px; height: 20px; }
.spark-bar { width: 3px; background: var(--text3); border-radius: 1px; }
.spark-bar.up { background: var(--green); }
.spark-bar.down { background: var(--red); }
</style>

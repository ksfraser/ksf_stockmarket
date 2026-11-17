<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
    --bg: #4a5568;
    --bg2: #5b6a82;
    --bg3: #6b7d96;
    --text: #f7fafc;
    --text2: #e2e8f0;
    --text3: #cbd5e0;
    --accent: #63b3ed;
    --accent2: #4299e1;
    --green: #68d391;
    --red: #fc8181;
    --yellow: #f6e05e;
    --orange: #ed8936;
    --border: #718096;
    --radius: 8px;
    --card-bg: #5a7a9e;
}
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Navigation ── */
.nav { background: #3d4a5c; border-bottom: 1px solid var(--border); padding: 0 20px; display: flex; align-items: center; gap: 8px; height: 56px; }
.nav-brand { font-weight: 700; font-size: 1.1em; color: var(--accent); margin-right: 20px; }
.nav a { padding: 8px 14px; border-radius: var(--radius); color: var(--text2); font-size: 0.9em; }
.nav a:hover, .nav a.active { background: var(--bg3); color: var(--text); text-decoration: none; }
.nav .right { margin-left: auto; color: var(--text3); font-size: 0.85em; }

/* ── Container ── */
.container { max-width: 1400px; margin: 0 auto; padding: 24px 20px; }

/* ── Cards ── */
.card { background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; margin-bottom: 20px; }
.card-header { font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text2); margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 12px; }

/* ── Stats Grid ── */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.stat-card { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: var(--radius); padding: 16px; text-align: center; }
.stat-value { font-size: 1.8em; font-weight: 700; color: #fff; }
.stat-label { font-size: 0.8em; color: var(--text3); margin-top: 4px; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
th { text-align: left; padding: 10px 12px; background: rgba(0,0,0,0.2); color: var(--text2); font-weight: 600; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em; position: sticky; top: 0; }
td { padding: 9px 12px; border-bottom: 1px solid rgba(255,255,255,0.08); }
tr:hover td { background: rgba(255,255,255,0.05); }
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
input[type="text"], select { background: rgba(0,0,0,0.2); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: var(--radius); font-size: 0.9em; }
input[type="text"]:focus { outline: none; border-color: var(--accent); }
.btn { display: inline-block; padding: 8px 16px; background: var(--accent2); color: #fff; border: none; border-radius: var(--radius); cursor: pointer; font-size: 0.88em; }
.btn:hover { background: var(--accent); text-decoration: none; }
.btn-sm { padding: 4px 10px; font-size: 0.8em; }

/* ── Chart container ── */
.chart-container { position: relative; width: 100%; height: 300px; }
.chart-lg { height: 400px; }

/* ── Search bar ── */
.search-bar { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
.search-bar input { flex: 1; }

/* ── Indicator grid ── */
.ind-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.ind-item { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius); padding: 12px; }
.ind-name { font-size: 0.75em; color: var(--text3); text-transform: uppercase; letter-spacing: 0.05em; }
.ind-value { font-size: 1.3em; font-weight: 600; margin-top: 4px; color: #fff; }

/* ── Bar ── */
.bar { height: 4px; background: rgba(0,0,0,0.2); border-radius: 2px; margin-top: 6px; overflow: hidden; }
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

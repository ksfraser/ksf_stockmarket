<?php
/**
 * DCF Valuation CSV Export — ksf_stockmarket
 *
 * A standalone report that calculates or accepts 5-year Discounted Cash Flow (DCF)
 * assumptions and produces intrinsic value + upside % for a single symbol/run,
 * then streams the result as a downloadable CSV.
 *
 * How to call:
 *   - Web (form):  /php/valuation_dcf.php
 *   - Web (CSV):   /php/valuation_dcf.php?download=1&symbol=AAPL&fiscal_year=2024&...
 *   - CLI:         php php/valuation_dcf.php --download --symbol AAPL ...
 *
 * Parameters (GET/POST/CLI):
 *   symbol             Ticker symbol (e.g. AAPL)
 *   fiscal_year        Base fiscal year for the valuation (e.g. 2024)
 *   base_revenue       Base revenue in absolute units (e.g. 389.5 for $389.5B)
 *   revenue_cagr       Revenue CAGR for projection horizon (decimal, e.g. 0.08)
 *   ebitda_margin      EBITDA margin as % of revenue (decimal, e.g. 0.35)
 *   da_pct             D&A as % of revenue (decimal, e.g. 0.04)
 *   capex_pct          CapEx as % of revenue (decimal, e.g. 0.05)
 *   nwc_pct            Net working capital investment as % of revenue (decimal, e.g. 0.02)
 *   tax_rate           Effective tax rate (decimal, default 0.25)
 *   wacc               Weighted average cost of capital (decimal, e.g. 0.09)
 *   terminal_growth    Perpetual growth rate (decimal, e.g. 0.025)
 *   net_debt           Net debt in absolute units
 *   shares_outstanding Shares outstanding in absolute units
 *   current_price      Current market price (optional; fetched from DB if available)
 *   assumptions_notes  Free-text notes on assumptions
 *   download           1 to force CSV download
 *
 * Sources:
 *   - Corporate Finance Institute — Valuation: https://corporatefinanceinstitute.com/resources/valuation/
 *   - Corporate Finance Institute — DCF Model Template: https://corporatefinanceinstitute.com/resources/templates/excel-models/dcf-model-template/
 *   - Corporate Finance Institute — DCF Model Training & Free Guide: https://corporatefinanceinstitute.com/resources/valuation/dcf-model-training-free-guide/
 *
 * Required config:
 *   - config.yaml at project root (optional; used for DB connection params + defaults)
 *   - Or environment variables: DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_CHARSET
 *   - Or fallback php/config/database.php
 *
 * CSV columns:
 *   symbol, as_of_date, fiscal_year, revenue_cagr, ebitda_margin, da_pct,
 *   capex_pct, nwc_pct, wacc, terminal_growth, terminal_value,
 *   pv_fcf_1..pv_fcf_5, sum_pv_fcf, enterprise_value, net_debt, equity_value,
 *   shares_outstanding, intrinsic_value_per_share, current_price, upside_pct,
 *   recommendation, assumptions_notes
 *
 * Usage examples:
 *   curl "http://localhost/php/valuation_dcf.php?download=1&symbol=AAPL&fiscal_year=2024&revenue_cagr=0.08&ebitda_margin=0.35&da_pct=0.04&capex_pct=0.05&nwc_pct=0.02&wacc=0.09&terminal_growth=0.025&net_debt=100&shares_outstanding=16000&current_price=185"
 */

// ---------------------------------------------------------------------------
// Bootstrap / autoload
// ---------------------------------------------------------------------------
error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

// Detect app root
$APP_ROOT = getenv('APP_ROOT');
if (!$APP_ROOT) {
    if (is_dir(__DIR__ . '/app/src/Controller')) {
        $APP_ROOT = realpath(__DIR__ . '/app');
    } elseif (is_dir(__DIR__ . '/src/Controller')) {
        $APP_ROOT = __DIR__;
    } else {
        $APP_ROOT = '/home/ksf_stockmarket/ksf_stockmarket';
    }
}
$GLOBALS['APP_ROOT'] = $APP_ROOT;

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function get_input(string $key, $default = null) {
    // CLI arguments first
    global $argv;
    if (isset($argv)) {
        foreach ($argv as $i => $arg) {
            if ($arg === '--' . $key) {
                return $argv[$i + 1] ?? $default;
            }
            if (str_starts_with($arg, '--' . $key . '=')) {
                return substr($arg, strlen('--' . $key . '='));
            }
        }
    }
    // POST/GET
    return $_REQUEST[$key] ?? $_GET[$key] ?? $_POST[$key] ?? $default;
}

function get_float(string $key, float $default): float {
    $val = get_input($key);
    return is_numeric($val) ? (float)$val : $default;
}

function get_string(string $key, string $default): string {
    $val = get_input($key);
    return is_string($val) ? trim($val) : $default;
}

function get_bool(string $key, bool $default): bool {
    $val = get_input($key);
    if ($val === null) return $default;
    $val = strtolower((string)$val);
    return in_array($val, ['1', 'true', 'yes', 'on'], true);
}

function absolute_path(string $p): string {
    return ltrim($p, '/\\');
}

// ---------------------------------------------------------------------------
// Database connection — reads config.yaml when possible, falls back to env/database.php
// ---------------------------------------------------------------------------
function get_connection(): PDO {
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }

    $dbhost = getenv('DB_HOST') ?: 'ksfraser.ca';
    $dbname = getenv('DB_NAME') ?: 'ksfraser_stock_market';
    $dbuser = getenv('DB_USER') ?: '';
    $dbpass = getenv('DB_PASS') ?: '';
    $charset = getenv('DB_CHARSET') ?: 'utf8mb4';

    // Try reading from config.yaml if yaml extension is available
    $cfgPath = rtrim($GLOBALS['APP_ROOT'], '/\\') . '/../config.yaml';
    if (file_exists($cfgPath) && function_exists('yaml_parse_file')) {
        try {
            $yaml = yaml_parse_file($cfgPath);
            if (is_array($yaml)) {
                // Check for nested data.* keys (config_loader pattern)
                if (isset($yaml['data']) && is_array($yaml['data'])) {
                    $dbhost = $yaml['data']['db_host'] ?? $dbhost;
                    $dbname = $yaml['data']['db_name'] ?? $dbname;
                    $dbuser = $yaml['data']['db_user'] ?? $dbuser;
                    $dbpass = $yaml['data']['db_password'] ?? $yaml['data']['db_pass'] ?? $dbpass;
                }
                // Flat keys in root
                $dbhost = $yaml['db_host'] ?? $dbhost;
                $dbname = $yaml['db_name'] ?? $dbname;
                $dbuser = $yaml['db_user'] ?? $dbuser;
                $dbpass = $yaml['db_password'] ?? $yaml['db_pass'] ?? $dbpass;
            }
        } catch (Throwable $e) {
            // ignore YAML parse errors, fall back to env/database.php below
        }
    }

    // Fallback to php/config/database.php
    $dbPhp = $GLOBALS['APP_ROOT'] . '/config/database.php';
    if (file_exists($dbPhp) && (!$dbuser || !$dbpass)) {
        try {
            $cfg = require $dbPhp;
            if (is_array($cfg)) {
                $dbhost = $cfg['host']     ?? $dbhost;
                $dbname = $cfg['database'] ?? $dbname;
                $dbuser = $cfg['username'] ?? $dbuser;
                $dbpass = $cfg['password'] ?? $dbpass;
                $charset = $cfg['charset'] ?? $charset;
            }
        } catch (Throwable $e) {
            // ignore
        }
    }

    $dsn = "mysql:host={$dbhost};dbname={$dbname};charset={$charset}";
    $pdo = new PDO($dsn, $dbuser, $dbpass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);

    return $pdo;
}

function fetch_latest_price(PDO $pdo, string $symbol): ?float {
    try {
        $resolved = $symbol;
        $stmt = $pdo->prepare('SELECT adj_close FROM stockprices WHERE symbol = :sym ORDER BY price_date DESC LIMIT 1');
        $stmt->execute([':sym' => $resolved]);
        $row = $stmt->fetch();
        if ($row && isset($row['adj_close'])) {
            return (float)$row['adj_close'];
        }
    } catch (Throwable $e) {
        // table may not exist
    }
    return null;
}

// ---------------------------------------------------------------------------
// DCF Calculation
// ---------------------------------------------------------------------------
function calculate_dcf(array $p): array {
    $baseRevenue   = (float)($p['base_revenue'] ?? 100.0);
    $cagr          = (float)($p['revenue_cagr'] ?? 0.05);
    $ebitdaMargin  = (float)($p['ebitda_margin'] ?? 0.30);
    $daPct         = (float)($p['da_pct'] ?? 0.03);
    $capexPct      = (float)($p['capex_pct'] ?? 0.04);
    $nwcPct        = (float)($p['nwc_pct'] ?? 0.01);
    $taxRate       = (float)($p['tax_rate'] ?? 0.25);
    $wacc          = (float)($p['wacc'] ?? 0.09);
    $terminalGrowth= (float)($p['terminal_growth'] ?? 0.025);
    $netDebt       = (float)($p['net_debt'] ?? 0.0);
    $sharesOut     = (float)($p['shares_outstanding'] ?? 1.0);
    $currentPrice  = (float)($p['current_price'] ?? 0.0);

    // Build 5-year FCFs
    $fcfs = [];
    $pvFcfs = [];
    $sumPvFcf = 0.0;
    $revenue = $baseRevenue;

    for ($year = 1; $year <= 5; $year++) {
        $revenue *= (1 + $cagr);
        // FCF = Revenue * [(EBITDA_margin - D&A%)*(1 - tax_rate) + D&A% - capex% - nwc%]
        $ebit = $revenue * ($ebitdaMargin - $daPct);
        $nopat = $ebit * (1 - $taxRate);
        $fcf = $nopat + ($revenue * $daPct) - ($revenue * $capexPct) - ($revenue * $nwcPct);
        $fcfs[$year] = $fcf;

        $discount = pow(1 + $wacc, $year);
        $pv = $fcf / $discount;
        $pvFcfs[$year] = $pv;
        $sumPvFcf += $pv;
    }

    // Terminal value (Gordon Growth) — only if WACC > terminal_growth
    if ($wacc > $terminalGrowth && $fcfs[5] > 0) {
        $terminalValue = $fcfs[5] * (1 + $terminalGrowth) / ($wacc - $terminalGrowth);
    } else {
        $terminalValue = 0.0;
    }
    $pvTerminal = $terminalValue / pow(1 + $wacc, 5);

    $enterpriseValue = $sumPvFcf + $pvTerminal;
    $equityValue = $enterpriseValue - $netDebt;
    $intrinsicPerShare = $sharesOut > 0 ? ($equityValue / $sharesOut) : 0.0;

    if ($currentPrice > 0) {
        $upsidePct = (($intrinsicPerShare / $currentPrice) - 1.0) * 100.0;
    } else {
        $upsidePct = null;
    }

    $recommendation = 'N/A';
    if ($upsidePct !== null) {
        if ($upsidePct > 20) $recommendation = 'Strong Buy';
        elseif ($upsidePct > 5) $recommendation = 'Buy';
        elseif ($upsidePct > -10) $recommendation = 'Hold';
        elseif ($upsidePct > -20) $recommendation = 'Sell';
        else $recommendation = 'Strong Sell';
    }

    return [
        'fcf'            => $fcfs,
        'pv_fcf'         => $pvFcfs,
        'terminal_value' => $terminalValue,
        'pv_terminal'    => $pvTerminal,
        'sum_pv_fcf'     => $sumPvFcf,
        'enterprise_value' => $enterpriseValue,
        'equity_value'   => $equityValue,
        'intrinsic_per_share' => $intrinsicPerShare,
        'upside_pct'     => $upsidePct,
        'recommendation' => $recommendation,
    ];
}

// ---------------------------------------------------------------------------
// Read inputs
// ---------------------------------------------------------------------------
$download = get_bool('download', false);

$symbol           = get_string('symbol', '');
$fiscalYear       = get_string('fiscal_year', date('Y'));
$baseRevenue      = get_float('base_revenue', 0);
$revenueCagr      = get_float('revenue_cagr', 0.05);
$ebitdaMargin     = get_float('ebitda_margin', 0.30);
$daPct            = get_float('da_pct', 0.03);
$capexPct         = get_float('capex_pct', 0.04);
$nwcPct           = get_float('nwc_pct', 0.01);
$taxRate          = get_float('tax_rate', 0.25);
$wacc             = get_float('wacc', 0.09);
$terminalGrowth   = get_float('terminal_growth', 0.025);
$netDebt          = get_float('net_debt', 0);
$sharesOutstanding= get_float('shares_outstanding', 0);
$currentPrice     = get_float('current_price', 0);
$assumptionsNotes = get_string('assumptions_notes', '');

// Try to fetch current price from DB if symbol provided and price not given
$pdo = null;
try {
    $pdo = get_connection();
    if ($symbol && $currentPrice <= 0) {
        $dbPrice = fetch_latest_price($pdo, $symbol);
        if ($dbPrice !== null) {
            $currentPrice = $dbPrice;
        }
    }
} catch (Throwable $e) {
    // DB not available; continue without it
    $pdo = null;
}

$asOfDate = date('Y-m-d');

// Build calculation params
$calcParams = [
    'base_revenue'      => $baseRevenue,
    'revenue_cagr'      => $revenueCagr,
    'ebitda_margin'     => $ebitdaMargin,
    'da_pct'            => $daPct,
    'capex_pct'         => $capexPct,
    'nwc_pct'           => $nwcPct,
    'tax_rate'          => $taxRate,
    'wacc'              => $wacc,
    'terminal_growth'   => $terminalGrowth,
    'net_debt'          => $netDebt,
    'shares_outstanding'=> $sharesOutstanding,
    'current_price'     => $currentPrice,
];

$result = calculate_dcf($calcParams);

// ---------------------------------------------------------------------------
// Persist to stock_dcf_valuations when symbol and fiscal_year are provided
// ---------------------------------------------------------------------------
$persistId = null;
if ($symbol !== '' && $fiscalYear !== '') {
    try {
        if ($pdo === null) {
            $pdo = get_connection();
        }

        $sql = 'INSERT INTO stock_dcf_valuations (
            symbol, as_of_date, fiscal_year,
            base_revenue, revenue_cagr, ebitda_margin, da_pct, capex_pct, nwc_pct,
            tax_rate, wacc, terminal_growth, net_debt, shares_outstanding,
            assumptions_notes,
            terminal_value, pv_fcf_1, pv_fcf_2, pv_fcf_3, pv_fcf_4, pv_fcf_5,
            sum_pv_fcf, enterprise_value, equity_value, intrinsic_value_per_share,
            current_price, upside_pct, recommendation
        ) VALUES (
            :symbol, :as_of_date, :fiscal_year,
            :base_revenue, :revenue_cagr, :ebitda_margin, :da_pct, :capex_pct, :nwc_pct,
            :tax_rate, :wacc, :terminal_growth, :net_debt, :shares_outstanding,
            :assumptions_notes,
            :terminal_value, :pv_fcf_1, :pv_fcf_2, :pv_fcf_3, :pv_fcf_4, :pv_fcf_5,
            :sum_pv_fcf, :enterprise_value, :equity_value, :intrinsic_value_per_share,
            :current_price, :upside_pct, :recommendation
        )';

        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            ':symbol'              => $symbol,
            ':as_of_date'          => $asOfDate,
            ':fiscal_year'         => (int)$fiscalYear,
            ':base_revenue'        => $baseRevenue,
            ':revenue_cagr'        => $revenueCagr,
            ':ebitda_margin'       => $ebitdaMargin,
            ':da_pct'              => $daPct,
            ':capex_pct'           => $capexPct,
            ':nwc_pct'             => $nwcPct,
            ':tax_rate'            => $taxRate,
            ':wacc'                => $wacc,
            ':terminal_growth'     => $terminalGrowth,
            ':net_debt'            => $netDebt,
            ':shares_outstanding'  => $sharesOutstanding,
            ':assumptions_notes'   => $assumptionsNotes ?: null,
            ':terminal_value'      => $result['terminal_value'],
            ':pv_fcf_1'            => $result['pv_fcf'][1] ?? 0,
            ':pv_fcf_2'            => $result['pv_fcf'][2] ?? 0,
            ':pv_fcf_3'            => $result['pv_fcf'][3] ?? 0,
            ':pv_fcf_4'            => $result['pv_fcf'][4] ?? 0,
            ':pv_fcf_5'            => $result['pv_fcf'][5] ?? 0,
            ':sum_pv_fcf'          => $result['sum_pv_fcf'],
            ':enterprise_value'    => $result['enterprise_value'],
            ':equity_value'        => $result['equity_value'],
            ':intrinsic_value_per_share' => $result['intrinsic_per_share'],
            ':current_price'       => $currentPrice,
            ':upside_pct'          => $result['upside_pct'],
            ':recommendation'      => $result['recommendation'],
        ]);
        $persistId = (int)$pdo->lastInsertId();
    } catch (Throwable $e) {
        // Persistence is best-effort; do not break the report
        $persistError = $e->getMessage();
    }
}

// ---------------------------------------------------------------------------
// CSV Export
// ---------------------------------------------------------------------------
function output_csv(array $row): void {
    $out = fopen('php://output', 'w');
    if ($out === false) {
        http_response_code(500);
        echo "Failed to open output stream";
        exit;
    }
    // Header
    $headers = [
        'symbol', 'as_of_date', 'fiscal_year', 'revenue_cagr', 'ebitda_margin',
        'da_pct', 'capex_pct', 'nwc_pct', 'wacc', 'terminal_growth',
        'terminal_value',
        'pv_fcf_1', 'pv_fcf_2', 'pv_fcf_3', 'pv_fcf_4', 'pv_fcf_5',
        'sum_pv_fcf', 'enterprise_value', 'net_debt', 'equity_value',
        'shares_outstanding', 'intrinsic_value_per_share', 'current_price',
        'upside_pct', 'recommendation', 'assumptions_notes'
    ];
    fputcsv($out, $headers);

    $rowData = [
        $row['symbol'],
        $row['as_of_date'],
        $row['fiscal_year'],
        number_format((float)$row['revenue_cagr'], 6, '.', ''),
        number_format((float)$row['ebitda_margin'], 6, '.', ''),
        number_format((float)$row['da_pct'], 6, '.', ''),
        number_format((float)$row['capex_pct'], 6, '.', ''),
        number_format((float)$row['nwc_pct'], 6, '.', ''),
        number_format((float)$row['wacc'], 6, '.', ''),
        number_format((float)$row['terminal_growth'], 6, '.', ''),
        number_format((float)$row['terminal_value'], 4, '.', ''),
    ];
    for ($i = 1; $i <= 5; $i++) {
        $rowData[] = number_format((float)$row['pv_fcf_' . $i], 4, '.', '');
    }
    $rowData[] = number_format((float)$row['sum_pv_fcf'], 4, '.', '');
    $rowData[] = number_format((float)$row['enterprise_value'], 4, '.', '');
    $rowData[] = number_format((float)$row['net_debt'], 4, '.', '');
    $rowData[] = number_format((float)$row['equity_value'], 4, '.', '');
    $rowData[] = number_format((float)$row['shares_outstanding'], 4, '.', '');
    $rowData[] = number_format((float)$row['intrinsic_value_per_share'], 4, '.', '');
    $rowData[] = number_format((float)$row['current_price'], 4, '.', '');
    $rowData[] = $row['upside_pct'] !== null ? number_format((float)$row['upside_pct'], 2, '.', '') : '';
    $rowData[] = $row['recommendation'];
    $rowData[] = $row['assumptions_notes'];

    fputcsv($out, $rowData);
    fclose($out);
}

if ($download || get_bool('csv', false)) {
    $filename = 'dcf_' . preg_replace('/[^A-Za-z0-9_\-]/', '_', $symbol ?: 'report') . '_' . date('Ymd') . '.csv';
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    header('Pragma: no-cache');
    header('Expires: 0');

    output_csv([
        'symbol'                     => $symbol,
        'as_of_date'                 => $asOfDate,
        'fiscal_year'                => $fiscalYear,
        'revenue_cagr'               => $revenueCagr,
        'ebitda_margin'              => $ebitdaMargin,
        'da_pct'                     => $daPct,
        'capex_pct'                  => $capexPct,
        'nwc_pct'                    => $nwcPct,
        'wacc'                       => $wacc,
        'terminal_growth'            => $terminalGrowth,
        'terminal_value'             => $result['terminal_value'],
        'pv_fcf_1'                   => $result['pv_fcf'][1] ?? 0,
        'pv_fcf_2'                   => $result['pv_fcf'][2] ?? 0,
        'pv_fcf_3'                   => $result['pv_fcf'][3] ?? 0,
        'pv_fcf_4'                   => $result['pv_fcf'][4] ?? 0,
        'pv_fcf_5'                   => $result['pv_fcf'][5] ?? 0,
        'sum_pv_fcf'                 => $result['sum_pv_fcf'],
        'enterprise_value'           => $result['enterprise_value'],
        'net_debt'                   => $netDebt,
        'equity_value'               => $result['equity_value'],
        'shares_outstanding'         => $sharesOutstanding,
        'intrinsic_value_per_share'  => $result['intrinsic_per_share'],
        'current_price'              => $currentPrice,
        'upside_pct'                 => $result['upside_pct'],
        'recommendation'             => $result['recommendation'],
        'assumptions_notes'          => $assumptionsNotes,
    ]);
    exit;
}

// ---------------------------------------------------------------------------
// HTML Report / Form (default)
// ---------------------------------------------------------------------------
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DCF Valuation Report — <?php echo htmlspecialchars($symbol ?: 'New'); ?></title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem; background: #f7f9fa; color: #212529; }
        .container { max-width: 960px; margin: 0 auto; background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
        h1 { font-size: 1.4rem; margin-bottom: 0.5rem; }
        .sub { color: #6c757d; margin-bottom: 1rem; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; }
        th, td { border: 1px solid #dee2e6; padding: 0.5rem; text-align: left; }
        th { background: #f1f3f5; width: 30%; }
        input[type="text"], input[type="number"], textarea { width: 100%; padding: 0.4rem; border: 1px solid #ced4da; border-radius: 4px; }
        textarea { resize: vertical; min-height: 60px; }
        .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
        button, .btn { padding: 0.55rem 1rem; border: none; border-radius: 4px; cursor: pointer; color: #fff; background: #0d6efd; text-decoration: none; display: inline-block; }
        button:hover, .btn:hover { background: #0b5ed7; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #5c636a; }
        .result { margin-top: 1.5rem; }
        .result h2 { font-size: 1.15rem; margin-bottom: 0.5rem; }
        .metric { display: inline-block; margin: 0.25rem 0.75rem 0.25rem 0; }
        .metric strong { color: #0d6efd; }
        .note { font-size: 0.85rem; color: #495057; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>DCF Valuation Report</h1>
        <p class="sub">Discounted Cash Flow (5-year) CSV export engine. Fill assumptions below, then calculate and download the CSV.</p>

        <form method="GET" action="">
            <table>
                <tr>
                    <th><label for="symbol">Symbol</label></th>
                    <td><input type="text" id="symbol" name="symbol" value="<?php echo htmlspecialchars($symbol); ?>" placeholder="AAPL"></td>
                </tr>
                <tr>
                    <th><label for="fiscal_year">Fiscal Year</label></th>
                    <td><input type="number" id="fiscal_year" name="fiscal_year" value="<?php echo htmlspecialchars($fiscalYear); ?>"></td>
                </tr>
                <tr>
                    <th><label for="base_revenue">Base Revenue (absolute)</label></th>
                    <td><input type="number" step="any" id="base_revenue" name="base_revenue" value="<?php echo htmlspecialchars($baseRevenue ?: '389.5'); ?>"></td>
                </tr>
                <tr>
                    <th><label for="revenue_cagr">Revenue CAGR</label></th>
                    <td><input type="number" step="any" id="revenue_cagr" name="revenue_cagr" value="<?php echo htmlspecialchars($revenueCagr); ?>"></td>
                </tr>
                <tr>
                    <th><label for="ebitda_margin">EBITDA Margin</label></th>
                    <td><input type="number" step="any" id="ebitda_margin" name="ebitda_margin" value="<?php echo htmlspecialchars($ebitdaMargin); ?>"></td>
                </tr>
                <tr>
                    <th><label for="da_pct">D&A % of Revenue</label></th>
                    <td><input type="number" step="any" id="da_pct" name="da_pct" value="<?php echo htmlspecialchars($daPct); ?>"></td>
                </tr>
                <tr>
                    <th><label for="capex_pct">CapEx % of Revenue</label></th>
                    <td><input type="number" step="any" id="capex_pct" name="capex_pct" value="<?php echo htmlspecialchars($capexPct); ?>"></td>
                </tr>
                <tr>
                    <th><label for="nwc_pct">NWC Investment % of Revenue</label></th>
                    <td><input type="number" step="any" id="nwc_pct" name="nwc_pct" value="<?php echo htmlspecialchars($nwcPct); ?>"></td>
                </tr>
                <tr>
                    <th><label for="tax_rate">Tax Rate</label></th>
                    <td><input type="number" step="any" id="tax_rate" name="tax_rate" value="<?php echo htmlspecialchars($taxRate); ?>"></td>
                </tr>
                <tr>
                    <th><label for="wacc">WACC</label></th>
                    <td><input type="number" step="any" id="wacc" name="wacc" value="<?php echo htmlspecialchars($wacc); ?>"></td>
                </tr>
                <tr>
                    <th><label for="terminal_growth">Terminal Growth</label></th>
                    <td><input type="number" step="any" id="terminal_growth" name="terminal_growth" value="<?php echo htmlspecialchars($terminalGrowth); ?>"></td>
                </tr>
                <tr>
                    <th><label for="net_debt">Net Debt (absolute)</label></th>
                    <td><input type="number" step="any" id="net_debt" name="net_debt" value="<?php echo htmlspecialchars($netDebt); ?>"></td>
                </tr>
                <tr>
                    <th><label for="shares_outstanding">Shares Outstanding (absolute)</label></th>
                    <td><input type="number" step="any" id="shares_outstanding" name="shares_outstanding" value="<?php echo htmlspecialchars($sharesOutstanding); ?>"></td>
                </tr>
                <tr>
                    <th><label for="current_price">Current Price (optional)</label></th>
                    <td><input type="number" step="any" id="current_price" name="current_price" value="<?php echo htmlspecialchars($currentPrice); ?>"></td>
                </tr>
                <tr>
                    <th><label for="assumptions_notes">Assumptions Notes</label></th>
                    <td><textarea id="assumptions_notes" name="assumptions_notes" placeholder="e.g. Conservative margin expansion, 3% terminal growth..."><?php echo htmlspecialchars($assumptionsNotes); ?></textarea></td>
                </tr>
            </table>
            <div class="actions">
                <button type="submit" name="download" value="1">Download CSV</button>
                <button type="submit" name="calculate" value="1">Calculate on Page</button>
                <a href="<?php echo strtok($_SERVER['REQUEST_URI'], '?'); ?>" class="btn btn-secondary">Reset</a>
            </div>
        </form>

        <div class="result">
            <h2>Valuation Result</h2>
            <?php if ($persistId !== null): ?>
                <p class="sub">✅ Saved to DB as run #<?php echo (int)$persistId; ?> on <?php echo htmlspecialchars($asOfDate); ?></p>
            <?php elseif (isset($persistError)): ?>
                <p class="sub">⚠️ Save skipped: <?php echo htmlspecialchars($persistError); ?></p>
            <?php endif; ?>
            <p><strong>Symbol:</strong> <?php echo htmlspecialchars($symbol ?: '—'); ?></p>
            <p><strong>As-of Date:</strong> <?php echo htmlspecialchars($asOfDate); ?></p>
            <span class="metric"><strong>Intrinsic Value / Share:</strong> $<?php echo number_format($result['intrinsic_per_share'], 2); ?></span>
            <span class="metric"><strong>Enterprise Value:</strong> $<?php echo number_format($result['enterprise_value'], 2); ?></span>
            <span class="metric"><strong>Equity Value:</strong> $<?php echo number_format($result['equity_value'], 2); ?></span>
            <br>
            <span class="metric"><strong>Terminal Value:</strong> $<?php echo number_format($result['terminal_value'], 2); ?></span>
            <span class="metric"><strong>Sum PV FCF:</strong> $<?php echo number_format($result['sum_pv_fcf'], 2); ?></span>
            <br>
            <span class="metric"><strong>Current Price:</strong> $<?php echo number_format($currentPrice, 2); ?></span>
            <span class="metric"><strong>Upside:</strong> <?php echo $result['upside_pct'] !== null ? number_format($result['upside_pct'], 2) . '%' : '—'; ?></span>
            <span class="metric"><strong>Recommendation:</strong> <?php echo htmlspecialchars($result['recommendation']); ?></span>
        </div>

        <div class="note">
            <p><strong>FCF Formula (per year):</strong> Revenue × [(EBITDA_margin − D&A%) × (1 − tax_rate) + D&A% − CapEx% − NWC%]</p>
            <p><strong>Terminal Value:</strong> FCF_Year5 × (1 + terminal_growth) / (WACC − terminal_growth)</p>
            <p>All monetary inputs (base_revenue, net_debt, shares_outstanding, current_price) are absolute. Percent inputs are decimals (e.g. 0.08 for 8%).</p>
        </div>
    </div>
</body>
</html>

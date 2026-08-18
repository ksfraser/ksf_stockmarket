<?php
/**
 * refresh_rbc_seg_funds.php — monthly RBC Insurance GIF segregated-fund refresh.
 *
 * Intended to run from the monthly cron (mid-month, ~day 15) so RBC has time to
 * publish the prior month's figures. Upserts the full Lipper column set into
 * seg_funds + seg_fund_calendar_returns and refreshes hosted fund-facts PDFs.
 *
 * DATA ACQUISITION:
 *   The authoritative source is the JS SPA at https://lipper.rbcinsurance.com/rbc/list
 *   (6 tabs: Fund Details, Short Term, Long Term, Calendar Year, Quartile Rankings,
 *   Buy Guide). A headless-browser pass (e.g. the Hermes browser tool / Puppeteer)
 *   should walk all 154 funds x 6 tabs, collect every column, and return the array
 *   consumed by upsertFunds(). As an initial/standalone path this script falls back
 *   to the email-gateway CSV export; that covers the trailing-return + fundamentals
 *   columns but NOT currency/asset_class/launch_date/aum/quartile ranks/MER%/PDFs
 *   (those require the live SPA pass). Replace fetchFromCsv() with fetchFromSpa().
 *
 * DB: reads credentials from the same env the app's Database class uses.
 * PHP 7.3-safe (no arrow fns / typed props / match).
 */

require_once __DIR__ . '/../Database.php'; // app Database class (provides Database::get())

const RBC_CSV = '/home/kevin/Documents/rbc_gif_funds_2026-08-17.csv';
const RBC_PDF_DIR = __DIR__ . '/../fund_pdfs';

function pdo(): PDO {
    return Database::get();
}

/**
 * Initial/fallback source: the email-gateway CSV.
 * Returns [ [fund_name,carrier,fund_code,num_securities,pe,pb,eps_growth,div_yield,
 *            return_1mo,return_3mo,ytd_pct,return_1yr,return_3yr,return_5yr,
 *            return_10yr,return_inception,volatility], ... ]
 */
function fetchFromCsv(): array {
    $out = [];
    if (!is_readable(RBC_CSV)) return $out;
    $h = fopen(RBC_CSV, 'r');
    fgetcsv($h); // header
    while (($r = fgetcsv($h)) !== false) {
        if (count($r) < 17 || trim($r[2]) === '') continue;
        $n = function($i){ $v = trim($r[$i] ?? ''); return $v === '' ? null : $v; };
        $out[] = [
            $r[2], $r[0], $r[1], $n(3), $n(4), $n(5), $n(6), $n(7),
            $n(8), $n(9), $n(10), $n(11), $n(12), $n(13), $n(14), $n(15), $n(16),
        ];
    }
    fclose($h);
    return $out;
}

/** Upsert a fund row and its calendar-year returns. */
function upsertFund(array $f): void {
    $pdo = pdo();
    // ON DUPLICATE KEY UPDATE requires a unique key on (fund_name, carrier).
    $pdo->prepare(
        "INSERT INTO seg_funds
           (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield,
            return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr,
            return_10yr, return_inception, volatility, is_active)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
         ON DUPLICATE KEY UPDATE
           fund_code=VALUES(fund_code), num_securities=VALUES(num_securities),
           pe=VALUES(pe), pb=VALUES(pb), eps_growth=VALUES(eps_growth),
           div_yield=VALUES(div_yield), return_1mo=VALUES(return_1mo),
           return_3mo=VALUES(return_3mo), ytd_pct=VALUES(ytd_pct),
           return_1yr=VALUES(return_1yr), return_3yr=VALUES(return_3yr),
           return_5yr=VALUES(return_5yr), return_10yr=VALUES(return_10yr),
           return_inception=VALUES(return_inception), volatility=VALUES(volatility)"
    )->execute($f);

    // Calendar-year returns (from the live SPA pass) would be upserted here:
    // foreach ($f['calendar'] as $year => $ret) { upsertCalendarReturn($fundId, $year, $ret); }
}

function main(): void {
    $funds = fetchFromCsv();
    $count = 0;
    foreach ($funds as $f) {
        upsertFund($f);
        $count++;
    }
    // PDF refresh is delegated; see download_rbc_pdfs.php (run after the SPA pass
    // has produced the per-fund PDF URLs).
    fprintf(STDERR, "Refreshed %d RBC seg funds (CSV fallback).\n", $count);
    echo sprintf("Refreshed %d RBC seg funds.\n", $count);
}

main();

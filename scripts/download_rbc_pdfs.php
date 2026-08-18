<?php
/**
 * download_rbc_pdfs.php — download RBC fund-facts / buy-guide PDFs and host them locally.
 *
 * Called by the monthly refresh after the SPA pass has produced a map of
 * fund_name => pdf_url. Downloads each PDF into fund_pdfs/ and updates
 * seg_funds.pdf_path so the fund detail page can link to it.
 *
 * Usage: php download_rbc_pdfs.php  (reads the URL map produced by the SPA scraper)
 *
 * NOTE: the PDF URL list must be supplied by the headless-browser SPA pass
 * (the "Link to PDF" per fund on lipper.rbcinsurance.com). This script takes a
 * JSON file (fund_pdfs_map.json) of {fund_name: pdf_url} and downloads them.
 */

const PDF_DIR = __DIR__ . '/../fund_pdfs';
const MAP_FILE = __DIR__ . '/fund_pdfs_map.json';

require_once __DIR__ . '/../Database.php';

function main(): void {
    if (!is_dir(PDF_DIR)) {
        mkdir(PDF_DIR, 0755, true);
    }
    if (!is_readable(MAP_FILE)) {
        fprintf(STDERR, "No PDF map at %s (produce it from the SPA pass first).\n", MAP_FILE);
        return;
    }
    $map = json_decode(file_get_contents(MAP_FILE), true);
    $pdo = Database::get();
    $ok = 0;
    foreach ($map as $fundName => $url) {
        $safe = preg_replace('/[^A-Za-z0-9_-]/', '_', $fundName) . '.pdf';
        $dest = PDF_DIR . '/' . $safe;
        $data = @file_get_contents($url);
        if ($data === false) {
            fprintf(STDERR, "FAILED: %s\n", $fundName);
            continue;
        }
        file_put_contents($dest, $data);
        $rel = 'fund_pdfs/' . $safe;
        $pdo->prepare("UPDATE seg_funds SET pdf_path=? WHERE fund_name=? AND carrier='RBC'")
            ->execute([$rel, $fundName]);
        $ok++;
    }
    echo sprintf("Downloaded %d fund PDFs to %s\n", $ok, PDF_DIR);
}

main();

<?php
/**
 * ExportController — Export transactions to OFX/QFX format.
 *
 * GET  /?action=export — Show export form with account selection.
 * POST /?action=export — Generate and download OFX file.
 */

class ExportController
{
    private PDO $pdo;

    public function __construct()
    {
        $this->pdo = Database::get();
    }

    /**
     * Route GET (form) and POST (download).
     */
    public function handle(): array
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            return $this->download();
        }
        return $this->form();
    }

    /**
     * GET — Show export form.
     */
    public function form(): array
    {
        $accounts = $this->getAccounts();

        return [
            'pageTitle' => 'Export Transactions (OFX)',
            'template'  => 'export',
            'accounts'  => $accounts,
        ];
    }

    /**
     * POST — Generate OFX and send as download.
     */
    public function download(): array
    {
        $accountType = $_POST['account_type'] ?? '';
        $startDate   = $_POST['start_date'] ?? '';
        $endDate     = $_POST['end_date'] ?? '';
        $format      = $_POST['format'] ?? 'ofx';  // ofx or qfx

        // Validate
        if (empty($accountType) || $accountType === 'ALL') {
            $accountType = null;  // Export all accounts
        }

        // Build filename
        $filename = $this->buildFilename($accountType, $startDate, $endDate, $format);

        // Call Python OFX exporter
        $ofxData = $this->generateOfx($accountType, $startDate, $endDate);

        if (empty($ofxData)) {
            return [
                'pageTitle' => 'Export Error',
                'template'  => 'export',
                'accounts'  => $this->getAccounts(),
                'error'     => 'No transactions found for the selected criteria.',
            ];
        }

        return [
            'raw_output' => true,
            'filename'   => $filename,
            'ofx_data'   => $ofxData,
        ];
    }

    /**
     * Get distinct account types with transaction counts.
     */
    private function getAccounts(): array
    {
        try {
            $stmt = $this->pdo->prepare("
                SELECT account_type, COUNT(*) as cnt,
                       MIN(trade_date) as earliest, MAX(trade_date) as latest
                FROM transactions
                WHERE account_type IS NOT NULL AND account_type != ''
                GROUP BY account_type
                ORDER BY account_type
            ");
            $stmt->execute();
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    /**
     * Call the Python OFX exporter and return the result.
     */
    private function generateOfx(?string $accountType, string $startDate, string $endDate): string
    {
        $script = '/var/www/stockmarket-app/scripts/pdf_parser/ofx_export.py';

        if (!file_exists($script)) {
            return '';
        }

        $cmd = ['/usr/bin/python3', $script];

        if ($accountType) {
            $cmd[] = '--account=' . $accountType;
        }
        if ($startDate) {
            $cmd[] = '--start=' . $startDate;
        }
        if ($endDate) {
            $cmd[] = '--end=' . $endDate;
        }
        $cmd[] = '--output=/tmp/ofx_export_' . uniqid() . '.ofx';

        $output = [];
        $exitCode = 0;
        exec(implode(' ', array_map('escapeshellarg', $cmd)) . ' 2>&1', $output, $exitCode);

        if ($exitCode !== 0) {
            return '';
        }

        // Read the generated file
        $tmpFile = end($cmd);
        $tmpFile = trim($tmpFile, "'");
        if (file_exists($tmpFile)) {
            $data = file_get_contents($tmpFile);
            @unlink($tmpFile);
            return $data;
        }

        return '';
    }

    /**
     * Build a descriptive filename.
     */
    private function buildFilename(?string $accountType, string $startDate, string $endDate, string $format): string
    {
        $parts = [];
        $parts[] = $accountType ?: 'all-accounts';
        if ($startDate) {
            $parts[] = $startDate;
        }
        if ($endDate) {
            $parts[] = 'to-' . $endDate;
        }
        $parts[] = date('Y-m-d');

        return 'transactions-' . implode('-', $parts) . '.' . $format;
    }
}

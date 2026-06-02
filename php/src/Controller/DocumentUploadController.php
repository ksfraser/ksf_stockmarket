<?php
/**
 * DocumentUploadController — Handles PDF/CSV upload, parsing, and import to transactions table.
 *
 * Supports:
 * - PDF account statements (CIBC Investor's Edge, etc.)
 * - CSV transaction exports
 * - Multi-file upload
 * - Drag-and-drop
 */
class DocumentUploadController
{
    private PDO $pdo;
    private string $uploadDir;
    private array $allowedExts = ['pdf', 'csv', 'txt'];
    private int $maxFileSize = 104857600; // 100MB

    public function __construct()
    {
        $this->pdo = Database::get();
        $this->uploadDir = '/var/www/stockmarket-app/uploads/documents/';
        if (!is_dir($this->uploadDir)) {
            mkdir($this->uploadDir, 0755, true);
        }
    }

    /**
     * GET /?action=upload — Display upload form.
     */
    public function form(): array
    {
        // Get import history
        $history = $this->getImportHistory();

        return [
            'pageTitle' => 'Upload Documents',
            'template'  => 'upload',
            'history'  => $history,
        ];
    }

    /**
     * POST /?action=upload&subaction=process — Process uploaded files.
     */
    public function process(): array
    {
        $results = [];
        $errors = [];

        if (empty($_FILES['documents'])) {
            return [
                'pageTitle' => 'Upload Documents',
                'template'  => 'upload',
                'error'     => 'No files uploaded.',
                'history'   => $this->getImportHistory(),
            ];
        }

        // Reorganize $_FILES array for multi-upload
        $files = $this->reorganizeFiles($_FILES['documents']);

        foreach ($files as $file) {
            if ($file['error'] !== UPLOAD_ERR_OK) {
                $errors[] = "{$file['name']}: " . $this->uploadError($file['error']);
                continue;
            }

            $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
            if (!in_array($ext, $this->allowedExts)) {
                $errors[] = "{$file['name']}: Invalid file type (.{$ext}). Allowed: " . implode(', ', $this->allowedExts);
                continue;
            }

            if ($file['size'] > $this->maxFileSize) {
                $errors[] = "{$file['name']}: File too large (" . $this->formatBytes($file['size']) . "). Max: " . $this->formatBytes($this->maxFileSize);
                continue;
            }

            // Save uploaded file
            $safeName = $this->safeFilename($file['name']);
            $destPath = $this->uploadDir . date('Ymd_His') . '_' . $safeName;

            if (!move_uploaded_file($file['tmp_name'], $destPath)) {
                $errors[] = "{$file['name']}: Failed to save file.";
                continue;
            }

            // Parse based on file type
            try {
                $parseResult = $this->parseFile($destPath, $ext);
                $results[] = [
                    'filename'  => $file['name'],
                    'saved_as'  => basename($destPath),
                    'type'      => $ext,
                    'parse'     => $parseResult,
                ];
            } catch (Exception $e) {
                $errors[] = "{$file['name']}: Parse error — " . $e->getMessage();
            }
        }

        return [
            'pageTitle' => 'Upload Results',
            'template'  => 'upload_results',
            'results'   => $results,
            'errors'    => $errors,
            'history'   => $this->getImportHistory(),
        ];
    }

    /**
     * Route upload actions.
     */
    public function handle(): array
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            return $this->process();
        }
        return $this->form();
    }

    // --- Private methods ---

    private function reorganizeFiles(array $files): array
    {
        $result = [];
        if (!is_array($files['name'])) {
            // Single file
            return [$files];
        }
        $count = count($files['name']);
        for ($i = 0; $i < $count; $i++) {
            $result[] = [
                'name'     => $files['name'][$i],
                'type'     => $files['type'][$i],
                'tmp_name' => $files['tmp_name'][$i],
                'error'    => $files['error'][$i],
                'size'     => $files['size'][$i],
            ];
        }
        return $result;
    }

    private function parseFile(string $path, string $ext): array
    {
        switch ($ext) {
            case 'csv':
            case 'txt':
                return $this->parseCsv($path);
            case 'pdf':
                return $this->parsePdf($path);
            default:
                throw new Exception("Unsupported file type: {$ext}");
        }
    }

    private function parseCsv(string $path): array
    {
        $handle = fopen($path, 'r');
        if (!$handle) throw new Exception("Cannot open CSV file");

        $headers = fgetcsv($handle);
        if (!$headers) throw new Exception("Empty CSV file");

        // Detect format — CIBC, Questrade, etc.
        $format = $this->detectCsvFormat($headers);
        $transactions = [];
        $lineNum = 2;

        while (($row = fgetcsv($handle)) !== false) {
            $lineNum++;
            if (count($row) !== count($headers)) continue;

            $data = array_combine($headers, $row);
            $txn = $this->extractTransaction($data, $format, $lineNum);
            if ($txn) $transactions[] = $txn;
        }
        fclose($handle);

        // Insert transactions
        $imported = $this->importTransactions($transactions);

        return [
            'format'       => $format,
            'total_rows'   => $lineNum - 2,
            'parsed'       => count($transactions),
            'imported'     => $imported,
            'skipped'      => count($transactions) - $imported,
        ];
    }

    private function parsePdf(string $path): array
    {
        // Use Python pymupdf for PDF parsing
        $script = '/var/www/stockmarket-app/scripts/parse_pdf_statement.py';
        $output = [];
        $exitCode = 0;

        if (file_exists($script)) {
            exec("/usr/bin/python3 " . escapeshellarg($script) . " " . escapeshellarg($path) . " 2>&1", $output, $exitCode);
            if ($exitCode === 0 && !empty($output)) {
                $result = json_decode(implode("\n", $output), true);
                if ($result && isset($result['transactions'])) {
                    $imported = $this->importTransactions($result['transactions']);
                    return [
                        'format'     => $result['format'] ?? 'pdf',
                        'total_rows' => count($result['transactions']),
                        'parsed'     => count($result['transactions']),
                        'imported'   => $imported,
                        'skipped'    => count($result['transactions']) - $imported,
                        'pages'      => $result['pages'] ?? null,
                        'account'    => $result['account'] ?? null,
                    ];
                }
            }
        }

        // Fallback — try pdftotext + regex parsing
        $text = shell_exec("pdftotext -layout " . escapeshellarg($path) . " - 2>/dev/null");
        if (empty($text)) {
            throw new Exception("Could not extract text from PDF. Install pdftotext or pymupdf.");
        }

        // Count pages
        $pages = preg_match_all('/\f/', $text) + 1;

        return [
            'format'     => 'pdf (text only)',
            'total_rows' => substr_count($text, "\n"),
            'parsed'     => 0,
            'imported'   => 0,
            'skipped'    => 0,
            'pages'      => $pages,
            'note'      => 'PDF text extracted. Set up parse_pdf_statement.py for automatic transaction extraction, or review manually.',
            'text_preview' => substr($text, 0, 2000),
        ];
    }

    private function detectCsvFormat(array $headers): string
    {
        $h = array_map('strtolower', array_map('trim', $headers));

        // CIBC Investor's Edge
        if (in_array('date', $h) && in_array('description', $h) && in_array('amount', $h)) {
            return 'cibc';
        }
        // Questrade
        if (in_array('trade date', $h) && in_array('symbol', $h) && in_array('quantity', $h)) {
            return 'questrade';
        }
        // Generic — has date, symbol, amount
        if (in_array('date', $h) && (in_array('symbol', $h) || in_array('ticker', $h))) {
            return 'generic';
        }

        return 'unknown';
    }

    private function extractTransaction(array $data, string $format, int $lineNum): ?array
    {
        $data = array_map('trim', $data);

        switch ($format) {
            case 'cibc':
                // CIBC format — map columns
                $date = $data['date'] ?? $data['Date'] ?? null;
                $desc = $data['description'] ?? $data['Description'] ?? '';
                $amount = $data['amount'] ?? $data['Amount'] ?? null;
                if (!$date || !$amount) return null;
                return [
                    'trade_date'   => $this->parseDate($date),
                    'type'         => ((float)$amount > 0) ? 'BUY' : 'SELL',
                    'symbol'       => $this->extractSymbol($desc),
                    'quantity'     => 0,
                    'price'        => abs((float)$amount),
                    'total'        => abs((float)$amount),
                    'commission'   => 0,
                    'account_type' => 'UNKNOWN',
                    'currency'     => 'CAD',
                    'notes'        => $desc,
                    'source_line'  => $lineNum,
                    'source_file'  => 'upload',
                ];

            case 'questrade':
            case 'generic':
                $date = $data['trade date'] ?? $data['Trade Date'] ?? $data['date'] ?? $data['Date'] ?? null;
                $symbol = $data['symbol'] ?? $data['Symbol'] ?? $data['ticker'] ?? '';
                $qty = $data['quantity'] ?? $data['Quantity'] ?? 0;
                $price = $data['price'] ?? $data['Price'] ?? 0;
                $action = $data['action'] ?? $data['Action'] ?? $data['type'] ?? $data['Type'] ?? 'BUY';
                if (!$date) return null;
                return [
                    'trade_date'   => $this->parseDate($date),
                    'type'         => strtoupper($action),
                    'symbol'       => $this->extractSymbol($symbol),
                    'quantity'     => (float)str_replace(',', '', (string)$qty),
                    'price'        => (float)str_replace(['$', ','], '', (string)$price),
                    'total'        => (float)(str_replace(['$', ','], '', $data['gross amount'] ?? $data['Gross Amount'] ?? 0)),
                    'commission'   => (float)(str_replace(['$', ','], '', $data['commission'] ?? $data['Commission'] ?? 0)),
                    'account_type' => $data['account'] ?? $data['Account'] ?? 'UNKNOWN',
                    'currency'     => $data['currency'] ?? $data['Currency'] ?? 'CAD',
                    'notes'        => $data['description'] ?? $data['Description'] ?? '',
                    'source_line'  => $lineNum,
                    'source_file'  => 'upload',
                ];

            default:
                return null;
        }
    }

    private function importTransactions(array $transactions): int
    {
        if (empty($transactions)) return 0;

        $imported = 0;
        $sql = "INSERT IGNORE INTO transactions 
                (symbol, trade_date, type, quantity, price, total, commission, account_type, currency, notes, source_file, source_line) 
                VALUES (:symbol, :trade_date, :type, :quantity, :price, :total, :commission, :account_type, :currency, :notes, :source_file, :source_line)";
        $stmt = $this->pdo->prepare($sql);

        foreach ($transactions as $txn) {
            try {
                $stmt->execute([
                    ':symbol'       => $txn['symbol'] ?? '',
                    ':trade_date'   => $txn['trade_date'],
                    ':type'         => $txn['type'],
                    ':quantity'     => $txn['quantity'] ?? 0,
                    ':price'        => $txn['price'] ?? 0,
                    ':total'        => $txn['total'] ?? 0,
                    ':commission'   => $txn['commission'] ?? 0,
                    ':account_type' => $txn['account_type'] ?? 'UNKNOWN',
                    ':currency'     => $txn['currency'] ?? 'CAD',
                    ':notes'        => $txn['notes'] ?? '',
                    ':source_file'  => $txn['source_file'] ?? 'upload',
                    ':source_line'  => $txn['source_line'] ?? 0,
                ]);
                if ($stmt->rowCount() > 0) $imported++;
            } catch (Exception $e) {
                // Skip duplicates / bad rows
            }
        }
        return $imported;
    }

    private function parseDate(string $date): string
    {
        // Try multiple date formats
        $formats = ['Y-m-d', 'm/d/Y', 'd/m/Y', 'M d, Y', 'Y/m/d', 'd-M-Y'];
        foreach ($formats as $fmt) {
            $d = DateTime::createFromFormat($fmt, trim($date));
            if ($d && $d->format($fmt) === trim($date)) {
                return $d->format('Y-m-d');
            }
        }
        // Fallback — strtotime
        $ts = strtotime($date);
        return $ts ? date('Y-m-d', $ts) : date('Y-m-d');
    }

    private function extractSymbol(string $text): string
    {
        // Extract stock symbol from text (e.g., "BUY 100 RY.TO" → "RY.TO")
        if (preg_match('/\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b/', $text, $m)) {
            return $m[1];
        }
        $text = trim($text);
        if (preg_match('/^[A-Za-z0-9.]+$/', $text) && strlen($text) <= 10) {
            return strtoupper($text);
        }
        return '';
    }

    private function safeFilename(string $name): string
    {
        return preg_replace('/[^a-zA-Z0-9._-]/', '_', $name);
    }

    private function uploadError(int $code): string
    {
        return match ($code) {
            UPLOAD_ERR_INI_SIZE   => 'File exceeds server upload limit',
            UPLOAD_ERR_FORM_SIZE  => 'File exceeds form limit',
            UPLOAD_ERR_PARTIAL    => 'File partially uploaded',
            UPLOAD_ERR_NO_FILE    => 'No file uploaded',
            UPLOAD_ERR_NO_TMP_DIR => 'Missing temp directory',
            UPLOAD_ERR_CANT_WRITE => 'Cannot write to disk',
            default               => 'Unknown upload error',
        };
    }

    private function formatBytes(int $bytes): string
    {
        $units = ['B', 'KB', 'MB', 'GB'];
        $i = 0;
        while ($bytes >= 1024 && $i < count($units) - 1) {
            $bytes /= 1024;
            $i++;
        }
        return round($bytes, 1) . ' ' . $units[$i];
    }

    private function getImportHistory(): array
    {
        try {
            $stmt = $this->pdo->query("
                SELECT source_file, COUNT(*) as txn_count, 
                       MIN(trade_date) as earliest, MAX(trade_date) as latest
                FROM transactions 
                WHERE source_file != ''
                GROUP BY source_file 
                ORDER BY latest DESC 
                LIMIT 20
            ");
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }
}

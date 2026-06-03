<?php
/**
 * DocumentUploadController — Handles PDF/CSV upload, parsing, and import to transactions table.
 *
 * Supports:
 * - PDF account statements (CIBC Investor's Edge, Questrade, generic)
 * - CSV transaction exports
 * - Multi-file drag-and-drop upload
 *
 * Files are stored temporarily and deleted immediately after processing.
 * Upload history (filename, status, errors) is recorded in the upload_log table.
 */
class DocumentUploadController
{
    private PDO $pdo;
    private string $uploadDir;
    private array $allowedExts = ['pdf', 'csv', 'txt'];
    private int $maxFileSize = 104857600; // 100MB
    private int $userId;

    public function __construct()
    {
        $this->pdo = Database::get();
        $this->uploadDir = '/var/www/stockmarket-app/uploads/documents/';
        if (!is_dir($this->uploadDir)) {
            mkdir($this->uploadDir, 0750, true);
        }
        $this->userId = AuthController::checkSession()['id'] ?? 0;
    }

    /**
     * GET /?action=upload — Display upload form with history.
     */
    public function form(): array
    {
        return [
            'pageTitle' => 'Upload Documents',
            'template'  => 'upload',
            'history'   => $this->getUploadHistory(),
        ];
    }

    /**
     * POST /?action=upload — Process uploaded files.
     */
    public function process(): array
    {
        $results = [];
        $errors  = [];

        if (empty($_FILES['documents'])) {
            return [
                'pageTitle' => 'Upload Documents',
                'template'  => 'upload',
                'error'     => 'No files uploaded.',
                'history'   => $this->getUploadHistory(),
            ];
        }

        $files = $this->reorganizeFiles($_FILES['documents']);

        foreach ($files as $file) {
            $startTime = microtime(true);
            $logId = null;

            // ── Phase 1: Upload validation ──────────────────────────────
            $uploadError = $this->validateUpload($file);
            if ($uploadError) {
                $errors[] = ['filename' => $file['name'], 'status' => 'error', 'error' => $uploadError];
                continue;
            }

            $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
            $safeName = $this->safeFilename($file['name']);
            $storedName = date('Ymd_His') . '_' . bin2hex(random_bytes(4)) . '_' . $safeName;
            $destPath  = $this->uploadDir . $storedName;

            // ── Phase 2: Move to temp storage ───────────────────────────
            if (!move_uploaded_file($file['tmp_name'], $destPath)) {
                $errors[] = ['filename' => $file['name'], 'status' => 'error',
                    'error' => 'Failed to save uploaded file. Check disk space and permissions.'];
                $this->logUpload(0, $file['name'], $storedName, $file['size'], $ext, 'error',
                    'move_uploaded_file failed — possible disk full or permission error');
                continue;
            }

            // ── Phase 3: Create upload_log entry ────────────────────────
            $logId = $this->logUpload($this->userId, $file['name'], $storedName, $file['size'], $ext, 'processing', null);

            // ── Phase 4: Parse file ─────────────────────────────────────
            try {
                $parseResult = $this->parseFile($destPath, $ext);
                $elapsed = (int)((microtime(true) - $startTime) * 1000);

                $this->updateUploadLog($logId, 'processed',
                    $parseResult['parsed'] ?? 0,
                    $parseResult['imported'] ?? 0,
                    $parseResult['skipped'] ?? 0,
                    $parseResult['format'] ?? 'unknown',
                    $elapsed,
                    null
                );

                $results[] = [
                    'filename' => $file['name'],
                    'status'   => 'processed',
                    'format'   => $parseResult['format'] ?? 'unknown',
                    'parsed'   => $parseResult['parsed'] ?? 0,
                    'imported' => $parseResult['imported'] ?? 0,
                    'skipped'  => $parseResult['skipped'] ?? 0,
                    'note'     => $parseResult['note'] ?? null,
                ];
            } catch (Exception $e) {
                $elapsed = (int)((microtime(true) - $startTime) * 1000);
                $errorMsg = $e->getMessage();

                $this->updateUploadLog($logId, 'error', 0, 0, 0, null, $elapsed, $errorMsg);

                $results[] = [
                    'filename' => $file['name'],
                    'status'   => 'error',
                    'error'    => $errorMsg,
                ];
            }

            // ── Phase 5: Always clean up temp file ─────────────────────
            @unlink($destPath);
        }

        return [
            'pageTitle' => 'Upload Results',
            'template'  => 'upload',
            'results'   => $results,
            'errors'    => $errors,
            'history'   => $this->getUploadHistory(),
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

    // ── Upload validation ─────────────────────────────────────────────────

    private function validateUpload(array $file): ?string
    {
        if ($file['error'] !== UPLOAD_ERR_OK) {
            return $this->uploadErrorMessage($file['error']);
        }

        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, $this->allowedExts)) {
            return "Invalid file type (.{$ext}). Allowed: " . implode(', ', $this->allowedExts);
        }

        if ($file['size'] > $this->maxFileSize) {
            return "File too large (" . $this->formatBytes($file['size']) . "). Max: " . $this->formatBytes($this->maxFileSize);
        }

        if ($file['size'] === 0) {
            return "File is empty (0 bytes).";
        }

        return null;
    }

    // ── Upload log DB operations ──────────────────────────────────────────

    private function logUpload(int $userId, string $originalName, string $storedName,
                                int $size, string $ext, string $status,
                                ?string $errorMsg): int
    {
        try {
            $stmt = $this->pdo->prepare("
                INSERT INTO upload_log (user_id, original_filename, stored_filename, file_size, file_type, status, error_message)
                VALUES (:uid, :orig, :stored, :size, :ext, :status, :err)
            ");
            $stmt->execute([
                ':uid' => $userId, ':orig' => $originalName, ':stored' => $storedName,
                ':size' => $size, ':ext' => $ext, ':status' => $status, ':err' => $errorMsg,
            ]);
            return (int)$this->pdo->lastInsertId();
        } catch (Exception $e) {
            return 0;
        }
    }

    private function updateUploadLog(int $logId, string $status, int $parsed, int $imported,
                                      int $skipped, ?string $format, int $elapsedMs,
                                      ?string $errorMsg): void
    {
        if (!$logId) return;
        try {
            $stmt = $this->pdo->prepare("
                UPDATE upload_log SET
                    status = :status,
                    rows_parsed = :parsed,
                    rows_imported = :imported,
                    rows_skipped = :skipped,
                    detected_format = :fmt,
                    processing_time_ms = :elapsed,
                    error_message = COALESCE(:err, error_message),
                    completed_at = NOW()
                WHERE id = :id
            ");
            $stmt->execute([
                ':status' => $status, ':parsed' => $parsed, ':imported' => $imported,
                ':skipped' => $skipped, ':fmt' => $format, ':elapsed' => $elapsedMs,
                ':err' => $errorMsg, ':id' => $logId,
            ]);
        } catch (Exception $e) { /* non-fatal */ }
    }

    /**
     * Get upload history for the current user.
     */
    private function getUploadHistory(): array
    {
        try {
            $stmt = $this->pdo->prepare("
                SELECT id, original_filename, file_size, file_type, status,
                       error_message, rows_parsed, rows_imported, rows_skipped,
                       detected_format, processing_time_ms, created_at, completed_at
                FROM upload_log
                WHERE user_id = :uid
                ORDER BY created_at DESC
                LIMIT 50
            ");
            $stmt->execute([':uid' => $this->userId]);
            return $stmt->fetchAll();
        } catch (Exception $e) {
            return [];
        }
    }

    // ── File parsing (unchanged logic, better error messages) ─────────────

    private function reorganizeFiles(array $files): array
    {
        $result = [];
        if (!is_array($files['name'])) return [$files];
        $count = count($files['name']);
        for ($i = 0; $i < $count; $i++) {
            $result[] = [
                'name' => $files['name'][$i], 'type' => $files['type'][$i],
                'tmp_name' => $files['tmp_name'][$i], 'error' => $files['error'][$i],
                'size' => $files['size'][$i],
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
        if (!$handle) throw new Exception("Cannot open CSV file. File may be corrupted or unreadable.");

        $headers = fgetcsv($handle);
        if (!$headers || count($headers) < 2) {
            fclose($handle);
            throw new Exception("CSV has no recognizable headers. Expected at least 2 columns. First line: " . implode(', ', $headers ?: ['(empty)']));
        }

        $format = $this->detectCsvFormat($headers);
        if ($format === 'unknown') {
            fclose($handle);
            throw new Exception("Unrecognized CSV format. Headers found: " . implode(', ', $headers) . ". Expected CIBC (Date, Description, Amount) or Questrade (Trade Date, Symbol, Quantity, Price) format.");
        }

        $transactions = [];
        $lineNum = 2;
        $emptyRows = 0;

        while (($row = fgetcsv($handle)) !== false) {
            $lineNum++;
            if (count($row) !== count($headers)) { $emptyRows++; continue; }
            if (implode('', array_map('trim', $row)) === '') { $emptyRows++; continue; }
            $data = array_combine($headers, $row);
            $txn = $this->extractTransaction($data, $format, $lineNum);
            if ($txn) $transactions[] = $txn;
        }
        fclose($handle);

        if (empty($transactions)) {
            throw new Exception("No transaction rows found in CSV. {$emptyRows} empty/malformed rows skipped. Check that the file contains trade data, not just a summary.");
        }

        $imported = $this->importTransactions($transactions);

        return [
            'format'     => $format,
            'total_rows' => $lineNum - 2,
            'parsed'     => count($transactions),
            'imported'   => $imported,
            'skipped'    => count($transactions) - $imported,
        ];
    }

    private function parsePdf(string $path): array
    {
        $script = '/var/www/stockmarket-app/scripts/parse_pdf_statement.py';

        if (file_exists($script)) {
            $output = [];
            $exitCode = 0;
            exec("/usr/bin/python3 " . escapeshellarg($script) . " " . escapeshellarg($path) . " --debug 2>&1", $output, $exitCode);

            if ($exitCode === 0 && !empty($output)) {
                $result = json_decode(implode("\n", $output), true);
                if ($result && isset($result['transactions'])) {
                    $imported = $this->importTransactions($result['transactions']);
                    return [
                        'format' => $result['format'] ?? 'pdf',
                        'total_rows' => count($result['transactions']),
                        'parsed' => count($result['transactions']),
                        'imported' => $imported,
                        'skipped' => count($result['transactions']) - $imported,
                        'pages' => $result['pages'] ?? null,
                        'account' => $result['account'] ?? null,
                        'note' => count($result['transactions']) === 0
                            ? 'PDF parsed but no transactions recognized. The statement format may not be supported yet. Try uploading as CSV export instead.'
                            : null,
                        'text_preview' => $result['text_preview'] ?? null,
                        'suspicious_lines' => $result['suspicious_lines'] ?? null,
                    ];
                }
            }

            // Python script ran but returned no usable data
            $stderr = implode("\n", array_slice($output, -5));
            throw new Exception("PDF parser returned no transactions. Exit code: {$exitCode}. Last output: " . ($stderr ?: '(empty)'));
        }

        // Fallback: pdftotext
        $text = shell_exec("pdftotext -layout " . escapeshellarg($path) . " - 2>/dev/null");
        if (empty($text)) {
            throw new Exception("Cannot extract text from PDF. Install pdftotext (poppler-utils) or pymupdf for full parsing.");
        }

        $pages = preg_match_all('/\f/', $text) + 1;
        return [
            'format'       => 'pdf (text only)',
            'total_rows'   => substr_count($text, "\n"),
            'parsed'       => 0,
            'imported'     => 0,
            'skipped'      => 0,
            'pages'        => $pages,
            'note'         => 'PDF text extracted but no automatic transaction parsing available. Install pymupdf and parse_pdf_statement.py for full import.',
            'text_preview' => substr($text, 0, 2000),
        ];
    }

    private function detectCsvFormat(array $headers): string
    {
        $h = array_map('strtolower', array_map('trim', $headers));
        if (in_array('date', $h) && in_array('description', $h) && in_array('amount', $h)) return 'cibc';
        if (in_array('trade date', $h) && in_array('symbol', $h) && in_array('quantity', $h)) return 'questrade';
        if (in_array('date', $h) && (in_array('symbol', $h) || in_array('ticker', $h))) return 'generic';
        return 'unknown';
    }

    private function extractTransaction(array $data, string $format, int $lineNum): ?array
    {
        $data = array_map('trim', $data);
        switch ($format) {
            case 'cibc':
                $date = $data['date'] ?? $data['Date'] ?? null;
                $desc = $data['description'] ?? $data['Description'] ?? '';
                $amount = $data['amount'] ?? $data['Amount'] ?? null;
                if (!$date || !$amount) return null;
                return [
                    'trade_date' => $this->parseDate($date), 'type' => ((float)$amount > 0) ? 'BUY' : 'SELL',
                    'symbol' => $this->extractSymbol($desc), 'quantity' => 0,
                    'price' => abs((float)$amount), 'total' => abs((float)$amount),
                    'commission' => 0, 'account_type' => 'UNKNOWN', 'currency' => 'CAD',
                    'notes' => $desc, 'source_line' => $lineNum, 'source_file' => 'upload',
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
                    'trade_date' => $this->parseDate($date), 'type' => strtoupper($action),
                    'symbol' => $this->extractSymbol($symbol),
                    'quantity' => (float)str_replace(',', '', (string)$qty),
                    'price' => (float)str_replace(['$', ','], '', (string)$price),
                    'total' => (float)(str_replace(['$', ','], '', $data['gross amount'] ?? $data['Gross Amount'] ?? 0)),
                    'commission' => (float)(str_replace(['$', ','], '', $data['commission'] ?? $data['Commission'] ?? 0)),
                    'account_type' => $data['account'] ?? $data['Account'] ?? 'UNKNOWN',
                    'currency' => $data['currency'] ?? $data['Currency'] ?? 'CAD',
                    'notes' => $data['description'] ?? $data['Description'] ?? '',
                    'source_line' => $lineNum, 'source_file' => 'upload',
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
                    ':symbol' => $txn['symbol'] ?? '', ':trade_date' => $txn['trade_date'],
                    ':type' => $txn['type'], ':quantity' => $txn['quantity'] ?? 0,
                    ':price' => $txn['price'] ?? 0, ':total' => $txn['total'] ?? 0,
                    ':commission' => $txn['commission'] ?? 0, ':account_type' => $txn['account_type'] ?? 'UNKNOWN',
                    ':currency' => $txn['currency'] ?? 'CAD', ':notes' => $txn['notes'] ?? '',
                    ':source_file' => $txn['source_file'] ?? 'upload', ':source_line' => $txn['source_line'] ?? 0,
                ]);
                if ($stmt->rowCount() > 0) $imported++;
            } catch (Exception $e) { /* skip duplicates / bad rows */ }
        }
        return $imported;
    }

    private function parseDate(string $date): string
    {
        $formats = ['Y-m-d', 'm/d/Y', 'd/m/Y', 'M d, Y', 'Y/m/d', 'd-M-Y'];
        foreach ($formats as $fmt) {
            $d = DateTime::createFromFormat($fmt, trim($date));
            if ($d && $d->format($fmt) === trim($date)) return $d->format('Y-m-d');
        }
        $ts = strtotime($date);
        return $ts ? date('Y-m-d', $ts) : date('Y-m-d');
    }

    private function extractSymbol(string $text): string
    {
        if (preg_match('/\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b/', $text, $m)) return $m[1];
        $text = trim($text);
        if (preg_match('/^[A-Za-z0-9.]+$/', $text) && strlen($text) <= 10) return strtoupper($text);
        return '';
    }

    private function safeFilename(string $name): string
    {
        return preg_replace('/[^a-zA-Z0-9._-]/', '_', $name);
    }

    private function uploadErrorMessage(int $code): string
    {
        return match ($code) {
            UPLOAD_ERR_INI_SIZE   => 'File exceeds server upload limit (check php.ini upload_max_filesize)',
            UPLOAD_ERR_FORM_SIZE  => 'File exceeds form limit',
            UPLOAD_ERR_PARTIAL    => 'File was only partially uploaded — try again',
            UPLOAD_ERR_NO_FILE    => 'No file was uploaded',
            UPLOAD_ERR_NO_TMP_DIR => 'Server error: missing temp directory',
            UPLOAD_ERR_CANT_WRITE => 'Server error: cannot write to disk (disk full or permission denied)',
            UPLOAD_ERR_EXTENSION  => 'Upload blocked by server extension',
            default               => 'Unknown upload error (code ' . $code . ')',
        };
    }

    private function formatBytes(int $bytes): string
    {
        $units = ['B', 'KB', 'MB', 'GB'];
        $i = 0;
        while ($bytes >= 1024 && $i < count($units) - 1) { $bytes /= 1024; $i++; }
        return round($bytes, 1) . ' ' . $units[$i];
    }
}

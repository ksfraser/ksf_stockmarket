<?php
/**
 * ReportController — Reports hub (TTWROR, securities, payments, tax lots, heat map).
 * Calls the Python API for computed reports.
 */
class ReportController {
    private $pdo;
    private $userId;
    private $apiBase;
    private $apiKey;

    public function __construct() {
        $this->pdo = Database::get();
        $user = AuthController::requireAuth();
        $this->userId = (int)($user['id'] ?? 1);
        $this->apiBase = rtrim($_ENV['PYTHON_API_URL'] ?? 'http://localhost:5000', '/');
        $this->apiKey = $_ENV['PYTHON_API_KEY'] ?? 'dev_key_change_me';
    }

    private function apiGet(string $path, array $params = []): array {
        $url = $this->apiBase . $path . '&' . http_build_query($params);
        $opts = [
            'http' => [
                'method' => 'GET',
                'header' => "X-API-Key: {$this->apiKey}\r\nX-User-Id: {$this->userId}\r\n",
                'timeout' => 10,
            ]
        ];
        $ctx = stream_context_create($opts);
        $json = @file_get_contents($url, false, $ctx);
        if ($json === false) {
            return ['error' => 'Python API unreachable', 'path' => $path];
        }
        $data = json_decode($json, true);
        return is_array($data) ? $data : ['error' => 'Invalid JSON', 'raw' => $json];
    }

    public function index(array $get): array {
        $report = $get['report'] ?? 'securities';
        $start = $get['start'] ?? (new DateTime('-1 year'))->format('Y-m-d');
        $end = $get['end'] ?? date('Y-m-d');
        $account = $get['account'] ?? '';
        $symbol = $get['symbol'] ?? '';
        $targetId = $get['target_id'] ?? '';
        $format = $get['format'] ?? 'html';

        $data = [
            'report' => $report,
            'start' => $start,
            'end' => $end,
            'account' => $account,
            'symbol' => $symbol,
            'target_id' => $targetId,
            'result' => null,
            'error' => null,
            'format' => $format,
        ];

        $q = http_build_query(array_filter([
            'start' => $start,
            'end' => $end,
            'account' => $account,
            'symbol' => $symbol,
            'user_id' => $this->userId,
            'format' => $format === 'csv' ? 'csv' : null,
        ]));

        switch ($report) {
            case 'twror':
                $data['result'] = $this->apiGet("/api/reports/twror?{$q}");
                break;
            case 'securities':
                $data['result'] = $this->apiGet("/api/reports/securities?{$q}");
                break;
            case 'payments':
                $data['result'] = $this->apiGet("/api/reports/payments?{$q}");
                break;
            case 'tax_lots':
                $data['result'] = $this->apiGet("/api/reports/tax_lots?{$q}");
                break;
            case 'heatmap':
                $data['result'] = $this->apiGet("/api/reports/heatmap?{$q}");
                break;
            case 'rebalance':
                $q2 = http_build_query(array_filter([
                    'start' => $start,
                    'end' => $end,
                    'account' => $account,
                    'symbol' => $symbol,
                    'user_id' => $this->userId,
                    'format' => $format === 'csv' ? 'csv' : null,
                ]));
                if ($targetId) {
                    $data['result'] = $this->apiGet("/api/reports/rebalance?action=compute&target_id=" . (int)$targetId . '&' . $q2);
                } else {
                    $data['result'] = $this->apiGet("/api/reports/rebalance?active=all&" . $q2);
                }
                break;
            default:
                $data['error'] = 'Unknown report type';
        }
        return $data;
    }

    private function exportCsv(string $report, string $start, string $end, string $account, string $symbol, string $targetId): void {
        $q = http_build_query(array_filter([
            'start' => $start,
            'end' => $end,
            'account' => $account,
            'symbol' => $symbol,
            'user_id' => $this->userId,
            'format' => 'csv',
        ]));
        $path = match($report) {
            'twror' => "/api/reports/twror?{$q}",
            'securities' => "/api/reports/securities?{$q}",
            'payments' => "/api/reports/payments?{$q}",
            'tax_lots' => "/api/reports/tax_lots?{$q}",
            'heatmap' => "/api/reports/heatmap?{$q}",
            'rebalance' => '/api/reports/rebalance?' . ($targetId ? 'action=compute&target_id=' . (int)$targetId . '&' : 'active=all&') . $q,
            default => throw new InvalidArgumentException('Unknown report type'),
        };
        $json = @file_get_contents($this->apiBase . $path, false, stream_context_create([
            'http' => [
                'method' => 'GET',
                'header' => "X-API-Key: {$this->apiKey}\r\nX-User-Id: {$this->userId}\r\n",
                'timeout' => 30,
            ]
        ]));
        $data = json_decode($json, true);
        if (!is_array($data)) {
            http_response_code(500);
            echo "CSV generation failed";
            exit;
        }
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="report_' . $report . '_' . date('Ymd') . '.csv"');
        $out = fopen('php://output', 'w');
        $this->arrayToCsv($out, $data);
        fclose($out);
        exit;
    }

    private function arrayToCsv($out, array $rows, ?array $headers = null): void {
        if ($headers === null) {
            $headers = $this->guessHeaders($rows);
        }
        fputcsv($out, $headers);
        foreach ($rows as $row) {
            fputcsv($out, $this->flattenRow($row, $headers));
        }
    }

    private function guessHeaders(array $rows): array {
        $headers = [];
        foreach ($rows as $row) {
            if (is_array($row)) {
                $headers = array_unique(array_merge($headers, array_keys($row)));
            }
        }
        return $headers;
    }

    private function flattenRow(array $row, array $headers): array {
        return array_map(fn($h) => is_array($row[$h] ?? null) ? json_encode($row[$h]) : (string)($row[$h] ?? ''), $headers);
    }
}

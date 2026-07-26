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

        $data = [
            'report' => $report,
            'start' => $start,
            'end' => $end,
            'account' => $account,
            'symbol' => $symbol,
            'target_id' => $targetId,
            'result' => null,
            'error' => null,
        ];

        $q = http_build_query(array_filter([
            'start' => $start,
            'end' => $end,
            'account' => $account,
            'symbol' => $symbol,
            'user_id' => $this->userId,
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
                if ($targetId) {
                    $data['result'] = $this->apiGet("/api/reports/rebalance?action=compute&target_id=" . (int)$targetId);
                } else {
                    $data['result'] = $this->apiGet("/api/reports/rebalance?active=all");
                }
                break;
            default:
                $data['error'] = 'Unknown report type';
        }
        return $data;
    }
}

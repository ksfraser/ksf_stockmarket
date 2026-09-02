<?php
/**
 * RebalancingController — manage rebalance targets and view drift.
 */
class RebalancingController {
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

    private function apiGet(string $path): array {
        $url = $this->apiBase . $path . '&user_id=' . $this->userId;
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

    private function apiPost(string $path, array $payload): array {
        $url = $this->apiBase . $path;
        $opts = [
            'http' => [
                'method' => 'POST',
                'header' => "Content-Type: application/json\r\nX-API-Key: {$this->apiKey}\r\nX-User-Id: {$this->userId}\r\n",
                'content' => json_encode($payload),
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

    public function index(array $get, array $post): array {
        $message = '';
        // POST: create/toggle/delete target
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = strtolower($post['action'] ?? '');
            if ($action === 'create' && !empty($post['name'])) {
                $allocations = [];
                foreach (($post['target_allocations'] ?? []) as $sym => $pct) {
                    $pct = (float)str_replace('%', '', $pct);
                    if ($sym && $pct > 0) {
                        $allocations[$sym] = $pct / 100;
                    }
                }
                $res = $this->apiPost('/api/reports/rebalance?' . http_build_query([
                    'action' => 'create',
                    'name' => $post['name'],
                    'target_type' => $post['target_type'] ?? 'taxonomy',
                    'target_allocations' => $allocations,
                    'tolerance_pct' => $post['tolerance_pct'] ?? 5,
                    'rebalance_frequency' => $post['rebalance_frequency'] ?? 'monthly',
                    'strategy_name' => $post['strategy_name'] ?: null,
                ]), []);
                $message = $res['target_id'] ? 'Target created' : ($res['error'] ?? 'Failed');
            } elseif ($action === 'toggle' && !empty($post['target_id'])) {
                $res = $this->apiPost('/api/reports/rebalance?' . http_build_query([
                    'action' => 'toggle',
                    'target_id' => (int)$post['target_id'],
                ]), ['active' => !empty($post['active'])]);
                $message = $res['status'] === 'toggled' ? 'Toggled' : ($res['error'] ?? 'Failed');
            } elseif ($action === 'delete' && !empty($post['target_id'])) {
                $res = $this->apiPost('/api/reports/rebalance?' . http_build_query([
                    'action' => 'delete',
                    'target_id' => (int)$post['target_id'],
                ]), []);
                $message = $res['status'] === 'deleted' ? 'Deleted' : ($res['error'] ?? 'Failed');
            }
        }

        $result = null;
        if (!empty($get['action']) && $get['action'] === 'compute' && !empty($get['target_id'])) {
            $result = $this->apiGet('/api/reports/rebalance?action=compute&target_id=' . (int)$get['target_id']);
        } else {
            $result = $this->apiGet('/api/reports/rebalance?active=all');
        }

        return [
            'message' => $message,
            'result' => $result,
            'get' => $get,
        ];
    }
}

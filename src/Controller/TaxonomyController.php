<?php
/**
 * TaxonomyController — manage taxonomy definitions + symbol assignments.
 */
class TaxonomyController {
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
        // POST: create/update/delete taxonomy or assignment
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $action = strtolower($post['action'] ?? '');
            if ($action === 'create' && !empty($post['name'])) {
                $res = $this->apiPost('/api/reports/taxonomies', [
                    'action' => 'create',
                    'name' => $post['name'],
                    'type' => $post['type'] ?? 'custom',
                    'parent_id' => $post['parent_id'] ? (int)$post['parent_id'] : null,
                ]);
                $message = $res['taxonomy_id'] ? 'Taxonomy created' : ($res['error'] ?? 'Failed');
            } elseif ($action === 'assign') {
                $res = $this->apiPost('/api/reports/taxonomies', [
                    'action' => 'assign',
                    'taxonomy_id' => (int)($post['taxonomy_id'] ?? 0),
                    'symbol' => strtoupper(trim($post['symbol'] ?? '')),
                    'weight' => (float)($post['weight'] ?? 0),
                    'notes' => $post['notes'] ?? '',
                ]);
                $message = $res['assignment_id'] ? 'Symbol assigned' : ($res['error'] ?? 'Failed');
            } elseif ($action === 'delete' && !empty($post['taxonomy_id'])) {
                $res = $this->apiPost('/api/reports/taxonomies', [
                    'action' => 'delete',
                    'taxonomy_id' => (int)$post['taxonomy_id'],
                ]);
                $message = $res['status'] === 'deleted' ? 'Deleted' : ($res['error'] ?? 'Failed');
            } elseif ($action === 'unassign' && !empty($post['assignment_id'])) {
                $res = $this->apiPost('/api/reports/taxonomies', [
                    'action' => 'unassign',
                    'assignment_id' => (int)$post['assignment_id'],
                ]);
                $message = $res['status'] === 'unassigned' ? 'Unassigned' : ($res['error'] ?? 'Failed');
            }
        }

        $data = $this->apiGet('/api/reports/taxonomies');
        $data['message'] = $message;
        return $data;
    }
}

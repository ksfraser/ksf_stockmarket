<?php
$path = '/home/ksf_stockmarket/ksf_stockmarket/php/src/Controller/SymbolAdminController.php';
$text = file_get_contents($path);

$old = <<<'PHP'
    public function listSymbols(string $filter = 'all', string $search = ''): array
    {
        $where = [];
        $params = [];

        if ($filter === 'inactive') {
            $where[] = 'sm.is_active = 0';
        } elseif ($filter === 'active') {
            $where[] = 'sm.is_active = 1';
        } elseif ($filter === 'no_exchange') {
            $where[] = '(sm.exchange IS NULL OR sm.exchange = \'\')';
        }

        if ($search) {
            $where[] = '(sm.symbol LIKE :search1 OR sm.name LIKE :search2)';
            $params[':search1'] = '%' . $search . '%';
            $params[':search2'] = '%' . $search . '%';
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        $sql = "SELECT sm.symbol, sm.name, COALESCE(NULLIF(sm.exchange, \'\'), em.exchange) as exchange, sm.sector, sm.is_active,
                       sm.deactivated_at, sm.deactivated_reason,
                       CASE WHEN sm.is_active = 0 THEN 'Inactive' ELSE 'Active' END as status_label
                FROM symbol_master sm
                LEFT JOIN exchange_mapping em ON sm.symbol = em.symbol AND em.is_primary = 1
                {$whereSql}
                ORDER BY sm.is_active DESC, sm.symbol
                LIMIT 500";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);

        return [
            'symbols'   => $stmt->fetchAll(),
            'filter'    => $filter,
            'search'    => $search,
            'total_active'   => $this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE is_active = 1")->fetchColumn(),
            'total_inactive' => $this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE is_active = 0")->fetchColumn(),
            'total_all'      => $this->pdo->query("SELECT COUNT(*) FROM symbol_master")->fetchColumn(),
        ];
    }
PHP;

$new = <<<'PHP'
    public function listSymbols(string $filter = 'all', string $search = '', int $page = 1, int $perPage = 500): array
    {
        $where = [];
        $params = [];

        if ($filter === 'inactive') {
            $where[] = 'sm.is_active = 0';
        } elseif ($filter === 'active') {
            $where[] = 'sm.is_active = 1';
        } elseif ($filter === 'no_exchange') {
            $where[] = '(sm.exchange IS NULL OR sm.exchange = \'\')';
        }

        if ($search) {
            $where[] = '(sm.symbol LIKE :search1 OR sm.name LIKE :search2)';
            $params[':search1'] = '%' . $search . '%';
            $params[':search2'] = '%' . $search . '%';
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        $countSql = "SELECT COUNT(*) FROM symbol_master sm LEFT JOIN exchange_mapping em ON sm.symbol = em.symbol AND em.is_primary = 1 {$whereSql}";
        $totalAll = (int)$this->pdo->query($countSql)->fetchColumn();

        $page = max(1, $page);
        $perPage = in_array($perPage, [50, 100, 250, 500, 1000]) ? $perPage : 500;
        $offset = ($page - 1) * $perPage;
        $totalPages = max(1, (int)ceil($totalAll / $perPage));
        if ($page > $totalPages) {
            $page = $totalPages;
            $offset = ($page - 1) * $perPage;
        }

        $sql = "SELECT sm.symbol, sm.name, COALESCE(NULLIF(sm.exchange, \'\'), em.exchange) as exchange, sm.sector, sm.is_active,
                       sm.deactivated_at, sm.deactivated_reason,
                       CASE WHEN sm.is_active = 0 THEN 'Inactive' ELSE 'Active' END as status_label
                FROM symbol_master sm
                LEFT JOIN exchange_mapping em ON sm.symbol = em.symbol AND em.is_primary = 1
                {$whereSql}
                ORDER BY sm.is_active DESC, sm.symbol
                LIMIT {$perPage} OFFSET {$offset}";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);

        return [
            'symbols'        => $stmt->fetchAll(),
            'filter'         => $filter,
            'search'         => $search,
            'page'           => $page,
            'per_page'       => $perPage,
            'total_all'      => $totalAll,
            'total_pages'    => $totalPages,
            'total_active'   => (int)$this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE is_active = 1")->fetchColumn(),
            'total_inactive' => (int)$this->pdo->query("SELECT COUNT(*) FROM symbol_master WHERE is_active = 0")->fetchColumn(),
        ];
    }
PHP;

if (strpos($text, $old) === false) {
    echo "OLD NOT FOUND\n";
    exit(1);
}

$text = str_replace($old, $new, $text);
file_put_contents($path, $text);
echo "OK\n";

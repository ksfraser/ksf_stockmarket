<?php
declare(strict_types=1);

/**
 * SymbolAdminController — manage symbol master data, exchange mappings, active/inactive status.
 */
class SymbolAdminController
{
    private PDO $pdo;

    public function __construct()
    {
        $this->pdo = Database::get();
    }

    /**
     * List all symbols with their active status and exchange mappings.
     */
    public function listSymbols(string $filter = 'all', string $search = '', int $page = 1, int $perPage = 500): array
    {
        $where = [];
        $params = [];

        if ($filter === 'inactive') {
            $where[] = 'sm.is_active = 0';
        } elseif ($filter === 'active') {
            $where[] = 'sm.is_active = 1';
        } elseif ($filter === 'no_exchange') {
            $where[] = '(sm.exchange IS NULL OR sm.exchange = "")';
        }

        if ($search) {
            $where[] = '(sm.symbol LIKE :search1 OR sm.name LIKE :search2)';
            $params[':search1'] = '%' . $search . '%';
            $params[':search2'] = '%' . $search . '%';
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        $countSql = "SELECT COUNT(*) FROM symbol_master sm LEFT JOIN exchange_mapping em ON sm.symbol = em.symbol AND em.is_primary = 1 {$whereSql}";
        $stmt = $this->pdo->prepare($countSql);
        $stmt->execute($params);
        $totalAll = (int)$stmt->fetchColumn();

        $page = max(1, $page);
        $perPage = in_array($perPage, [50, 100, 250, 500, 1000]) ? $perPage : 500;
        $offset = ($page - 1) * $perPage;
        $totalPages = max(1, (int)ceil($totalAll / $perPage));
        if ($page > $totalPages) {
            $page = $totalPages;
            $offset = ($page - 1) * $perPage;
        }

        $sql = "SELECT sm.symbol, sm.name, COALESCE(NULLIF(sm.exchange, ''), em.exchange) as exchange, sm.sector, sm.is_active,
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

    /**
     * Toggle symbol active status.
     */
    public function toggleActive(string $symbol): bool
    {
        $current = $this->pdo->prepare("SELECT is_active FROM symbol_master WHERE symbol = ?");
        $current->execute([$symbol]);
        $row = $current->fetch();
        if (!$row) return false;

        $newStatus = $row['is_active'] ? 0 : 1;
        $sql = $newStatus
            ? "UPDATE symbol_master SET is_active = 1, deactivated_at = NULL, deactivated_reason = NULL WHERE symbol = ?"
            : "UPDATE symbol_master SET is_active = 0, deactivated_at = NOW() WHERE symbol = ?";

        $stmt = $this->pdo->prepare($sql);
        return $stmt->execute([$symbol]);
    }

    /**
     * Set deactivation reason.
     */
    public function setDeactivationReason(string $symbol, string $reason): bool
    {
        $sql = "UPDATE symbol_master SET deactivated_reason = ?, deactivated_at = NOW(), is_active = 0 WHERE symbol = ?";
        $stmt = $this->pdo->prepare($sql);
        return $stmt->execute([$reason, $symbol]);
    }

    /**
     * List exchange mappings.
     */
    public function listExchangeMappings(): array
    {
        $sql = "SELECT em.*, sm.name as symbol_name
                FROM exchange_mapping em
                LEFT JOIN symbol_master sm ON em.symbol = sm.symbol
                ORDER BY em.symbol";
        return $this->pdo->query($sql)->fetchAll();
    }

    /**
     * Upsert exchange mapping.
     */
    public function saveExchangeMapping(array $data): bool
    {
        $sql = "INSERT INTO exchange_mapping (symbol, exchange, data_source, yahoo_ticker, is_primary, notes)
                VALUES (:symbol, :exchange, :data_source, :yahoo_ticker, 1, :notes)
                ON DUPLICATE KEY UPDATE
                    exchange = VALUES(exchange),
                    yahoo_ticker = VALUES(yahoo_ticker),
                    notes = VALUES(notes),
                    is_active = 1";

        $stmt = $this->pdo->prepare($sql);
        return $stmt->execute([
            ':symbol'      => $data['symbol'],
            ':exchange'    => $data['exchange'],
            ':data_source' => $data['data_source'] ?? 'yahoo',
            ':yahoo_ticker'=> $data['yahoo_ticker'] ?? $data['symbol'],
            ':notes'       => $data['notes'] ?? null,
        ]);
    }

    /**
     * Get active symbols only (for price fetcher).
     */
    public function getActiveSymbolsForFetch(): array
    {
        $sql = "SELECT sm.symbol, sm.exchange, em.yahoo_ticker, em.data_source
                FROM symbol_master sm
                LEFT JOIN exchange_mapping em ON sm.symbol = em.symbol AND em.is_active = 1
                WHERE sm.is_active = 1
                AND (sm.is_portfolio = 1 OR sm.is_watchlist = 1)";
        return $this->pdo->query($sql)->fetchAll();
    }

    /**
     * Add symbol to watchlist for tracking (without portfolio ownership).
     */
    public function addToWatchlist(array $data): bool
    {
        $sql = "INSERT INTO watchlist_symbols 
                (symbol, list_type, monitor_volume, monitor_price, volume_spike_threshold, notes, is_active)
                VALUES (:symbol, :list_type, :monitor_volume, :monitor_price, :volume_spike_threshold, :notes, 1)
                ON DUPLICATE KEY UPDATE
                    list_type = VALUES(list_type),
                    monitor_volume = VALUES(monitor_volume),
                    monitor_price = VALUES(monitor_price),
                    volume_spike_threshold = VALUES(volume_spike_threshold),
                    notes = VALUES(notes),
                    is_active = 1";

        $stmt = $this->pdo->prepare($sql);
        return $stmt->execute([
            ':symbol'               => $data['symbol'],
            ':list_type'            => $data['list_type'] ?? 'watchlist',
            ':monitor_volume'       => $data['monitor_volume'] ?? 1,
            ':monitor_price'        => $data['monitor_price'] ?? 0,
            ':volume_spike_threshold' => $data['volume_spike_threshold'] ?? 3.0,
            ':notes'                => $data['notes'] ?? null,
        ]);
    }

    /**
     * Remove symbol from watchlist.
     */
    public function removeFromWatchlist(string $symbol): bool
    {
        $sql = "DELETE FROM watchlist_symbols WHERE symbol = ? AND list_type = 'watchlist'";
        $stmt = $this->pdo->prepare($sql);
        return $stmt->execute([$symbol]);
    }

    /**
     * List all symbols in watchlist (for tracking).
     */
    public function listWatchlistSymbols(): array
    {
        $sql = "SELECT symbol, monitor_volume, monitor_price, volume_spike_threshold, notes, is_active, added_at
                FROM watchlist_symbols 
                WHERE list_type = 'watchlist'
                ORDER BY added_at DESC";
        return $this->pdo->query($sql)->fetchAll();
    }
}

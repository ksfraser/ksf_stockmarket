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
    public function listSymbols(string $filter = 'all', string $search = ''): array
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
            $where[] = '(sm.symbol LIKE :search OR sm.name LIKE :search)';
            $params[':search'] = '%' . $search . '%';
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        $sql = "SELECT sm.symbol, sm.name, sm.exchange, sm.sector, sm.is_active,
                       sm.deactivated_at, sm.deactivated_reason,
                       CASE WHEN sm.is_active = 0 THEN 'Inactive' ELSE 'Active' END as status_label
                FROM symbol_master sm
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
}

<?php

declare(strict_types=1);

/**
 * TransactionRepository — data access layer for the `transactions` table.
 *
 * Encapsulates all SQL for transaction history, settlement dates, and cash
 * calculations. Removes direct PDO calls from controller classes so that
 * schema changes only touch this file.
 *
 * Table schema (database/schema_transactions.sql):
 *   id, user_id, symbol, trade_date, type, quantity, price, total,
 *   commission, account_type, notes, source_file, source_line, created_at, updated_at
 */
class TransactionRepository
{
    private ?PDO $pdo = null;

    public function __construct(?PDO $pdo = null)
    {
        $this->pdo = $pdo ?? Database::get();
    }

    private function getPdo(): PDO
    {
        if ($this->pdo === null) {
            $this->pdo = Database::get();
        }
        return $this->pdo;
    }

    // ── Settlement dates ──────────────────────────────────────────────────────

    /**
     * Get latest trade date per symbol for a user (for T+2 settlement).
     *
     * @param int $userId
     * @param string[] $symbols
     * @return string[] mapping symbol => latest_trade_date
     */
    public function getLatestTradeDates(int $userId, array $symbols): array
    {
        if (empty($symbols)) {
            return [];
        }

        $in = implode(',', array_fill(0, count($symbols), '?'));
        $sql = "
            SELECT symbol, MAX(trade_date) as settlement_date
            FROM transactions
            WHERE user_id = ?
              AND symbol IN ($in)
              AND trade_date IS NOT NULL
            GROUP BY symbol
        ";

        $stmt = $this->getPdo()->prepare($sql);
        $stmt->execute(array_merge([$userId], $symbols));

        $result = [];
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
            $result[$row['symbol']] = $row['settlement_date'];
        }
        return $result;
    }

    // ── Cash calculation ──────────────────────────────────────────────────────

    /**
     * Calculate available cash (net of all settled transactions).
     *
     * @param int $userId
     * @return float cash amount in base currency (CAD)
     */
    public function getAvailableCash(int $userId): float
    {
        $sql = "
            SELECT COALESCE(SUM(
                CASE type
                    WHEN 'BUY' THEN -total
                    WHEN 'SELL' THEN total
                    WHEN 'DEPOSIT' THEN total
                    WHEN 'WITHDRAWAL' THEN -total
                    WHEN 'DIVIDEND' THEN total
                    WHEN 'INTEREST_CHARGE' THEN -total
                    WHEN 'TAX' THEN -total
                    WHEN 'DELIVERY' THEN -total
                    ELSE 0
                END
            ), 0) as cash
            FROM transactions
            WHERE user_id = :uid
              AND account_type IN ('portfolio', 'accrual')
              AND symbol = 'CASH'
              AND trade_date <= CURRENT_DATE()
        ";

        $stmt = $this->getPdo()->prepare($sql);
        $stmt->execute(['uid' => $userId]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        return (float)($row['cash'] ?? 0);
    }

    // ── Portfolio accounts ────────────────────────────────────────────────────

    /**
     * List active portfolio accounts for a user.
     *
     * @param int $userId
     * @return array<int, array<string, mixed>>
     */
    public function listPortfolioAccounts(int $userId): array
    {
        $sql = "
            SELECT id, institution, account_nickname, registration_type, currency
            FROM portfolio_accounts
            WHERE user_id = :uid AND is_active = 1
            ORDER BY registration_type, institution, account_nickname
        ";

        $stmt = $this->getPdo()->prepare($sql);
        $stmt->execute(['uid' => $userId]);
        return $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];
    }
}

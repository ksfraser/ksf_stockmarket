<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Model;

use PDO;
use InvalidArgumentException;

/**
 * Modern portfolio model.
 *
 * Works with the schema_v2 `portfolio` table structure:
 *   id, user_id, symbol, shares, cost_basis, cost_total,
 *   account_type, acquisition_date, is_active, updated_at
 *
 * Supports multiple account types (RRSP, TFSA, MARGIN, RESP, CASH).
 */
class Portfolio
{
    private PDO $db;

    public function __construct()
    {
        $this->db = Database::getConnection();
    }

    /**
     * Get all active positions for a user.
     */
    public function getHoldings(int $userId, ?string $accountType = null): array
    {
        $sql = 'SELECT * FROM portfolio WHERE user_id = :uid AND is_active = 1';
        $params = ['uid' => $userId];

        if ($accountType) {
            $sql .= ' AND account_type = :at';
            $params['at'] = $accountType;
        }

        $sql .= ' ORDER BY account_type, symbol';

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    /**
     * Get a single position.
     */
    public function getPosition(int $userId, string $symbol, string $accountType = 'CASH'): ?array
    {
        $stmt = $this->db->prepare(
            'SELECT * FROM portfolio
             WHERE user_id = :uid AND symbol = :sym AND account_type = :at AND is_active = 1'
        );
        $stmt->execute(['uid' => $userId, 'sym' => strtoupper($symbol), 'at' => $accountType]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Add or update a position.
     */
    public function setPosition(int $userId, string $symbol, float $shares,
                                 float $costBasis, string $accountType = 'CASH',
                                 ?string $acquisitionDate = null): int
    {
        if ($shares < 0) {
            throw new InvalidArgumentException('Shares cannot be negative');
        }

        $costTotal = $shares * $costBasis;
        $symbol = strtoupper($symbol);

        // Check if position exists
        $existing = $this->getPosition($userId, $symbol, $accountType);

        if ($existing) {
            // Update existing
            $stmt = $this->db->prepare(
                'UPDATE portfolio SET shares = :shares, cost_basis = :cb, cost_total = :ct
                 WHERE id = :id'
            );
            $stmt->execute([
                'shares' => $shares, 'cb' => $costBasis, 'ct' => $costTotal,
                'id' => $existing['id'],
            ]);
            return (int) $existing['id'];
        }

        // Insert new
        $stmt = $this->db->prepare(
            'INSERT INTO portfolio (user_id, symbol, shares, cost_basis, cost_total,
                                    account_type, acquisition_date, is_active)
             VALUES (:uid, :sym, :shares, :cb, :ct, :at, :ad, 1)'
        );
        $stmt->execute([
            'uid' => $userId, 'sym' => $symbol, 'shares' => $shares,
            'cb' => $costBasis, 'ct' => $costTotal, 'at' => $accountType,
            'ad' => $acquisitionDate ?? date('Y-m-d'),
        ]);

        return (int) $this->db->lastInsertId();
    }

    /**
     * Deactivate a position (don't delete — keep history).
     */
    public function deactivatePosition(int $userId, string $symbol, string $accountType = 'CASH'): bool
    {
        $stmt = $this->db->prepare(
            'UPDATE portfolio SET is_active = 0
             WHERE user_id = :uid AND symbol = :sym AND account_type = :at'
        );
        $stmt->execute(['uid' => $userId, 'sym' => strtoupper($symbol), 'at' => $accountType]);
        return $stmt->rowCount() > 0;
    }

    /**
     * Record a trade in user_trades table.
     */
    public function recordTrade(int $userId, string $symbol, string $action,
                                 float $shares, float $price, float $commission = 9.95,
                                 string $accountType = 'CASH', ?string $notes = null): int
    {
        $totalAmount = ($shares * $price) + ($action === 'BUY' ? $commission : -$commission);

        $stmt = $this->db->prepare(
            'INSERT INTO user_trades (user_id, symbol, action, shares, price, commission,
                                      total_amount, account_type, trade_date, notes)
             VALUES (:uid, :sym, :action, :shares, :price, :comm, :total, :at, CURDATE(), :notes)'
        );
        $stmt->execute([
            'uid' => $userId, 'sym' => strtoupper($symbol), 'action' => $action,
            'shares' => $shares, 'price' => $price, 'comm' => $commission,
            'total' => $totalAmount, 'at' => $accountType, 'notes' => $notes,
        ]);

        return (int) $this->db->lastInsertId();
    }

    /**
     * Get trade history for a user.
     */
    public function getTrades(int $userId, int $limit = 100): array
    {
        $stmt = $this->db->prepare(
            'SELECT * FROM user_trades WHERE user_id = :uid ORDER BY trade_date DESC, id DESC LIMIT :lim'
        );
        $stmt->bindValue('uid', $userId, PDO::PARAM_INT);
        $stmt->bindValue('lim', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /**
     * Get portfolio summary (total value by account type).
     */
    public function getSummary(int $userId): array
    {
        $stmt = $this->db->prepare(
            'SELECT account_type,
                    COUNT(*) as num_positions,
                    SUM(cost_total) as total_cost,
                    SUM(shares) as total_shares
             FROM portfolio
             WHERE user_id = :uid AND is_active = 1
             GROUP BY account_type
             ORDER BY account_type'
        );
        $stmt->execute(['uid' => $userId]);
        return $stmt->fetchAll();
    }
}

<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Model;

use PDO;
use InvalidArgumentException;
use RuntimeException;

/**
 * Portfolio model — represents a user's holdings.
 *
 * Modernized from class/portfolio.class.php.cpp
 */
class Portfolio
{
    private PDO $db;

    public function __construct()
    {
        $this->db = Database::getConnection();
    }

    /**
     * Get all positions for a user.
     *
     * @param string $user Username
     * @return array<int, array{symbol: string, shares: int, cost_basis: float, user: string}>
     */
    public function getPositions(string $user = 'default'): array
    {
        $stmt = $this->db->prepare(
            'SELECT symbol, number AS shares, cost AS cost_basis, user
             FROM portfolio
             WHERE user = :user
             ORDER BY symbol'
        );
        $stmt->execute(['user' => $user]);

        return $stmt->fetchAll();
    }

    /**
     * Get a single position.
     *
     * @param string $symbol Stock symbol
     * @param string $user   Username
     * @return array{symbol: string, shares: int, cost_basis: float}|null
     */
    public function getPosition(string $symbol, string $user = 'default'): ?array
    {
        $stmt = $this->db->prepare(
            'SELECT symbol, number AS shares, cost AS cost_basis
             FROM portfolio
             WHERE symbol = :symbol AND user = :user'
        );
        $stmt->execute(['symbol' => $symbol, 'user' => $user]);

        $result = $stmt->fetch();

        return $result ?: null;
    }

    /**
     * Add or update a position.
     *
     * @param string $symbol  Stock symbol
     * @param int    $shares  Number of shares
     * @param float  $cost    Total cost in dollars
     * @param string $user    Username
     */
    public function setPosition(string $symbol, int $shares, float $cost, string $user = 'default'): void
    {
        if ($shares < 0) {
            throw new InvalidArgumentException('Shares cannot be negative');
        }
        if ($cost < 0) {
            throw new InvalidArgumentException('Cost cannot be negative');
        }

        $stmt = $this->db->prepare(
            'INSERT INTO portfolio (symbol, number, cost, user)
             VALUES (:symbol, :shares, :cost, :user)
             ON DUPLICATE KEY UPDATE number = VALUES(number), cost = VALUES(cost)'
        );

        $stmt->execute([
            'symbol' => strtoupper($symbol),
            'shares' => $shares,
            'cost' => (int) round($cost * 100), // Store as cents
            'user' => $user,
        ]);
    }

    /**
     * Remove a position.
     *
     * @param string $symbol Stock symbol
     * @param string $user   Username
     * @return bool True if position was removed
     */
    public function removePosition(string $symbol, string $user = 'default'): bool
    {
        $stmt = $this->db->prepare(
            'DELETE FROM portfolio WHERE symbol = :symbol AND user = :user'
        );
        $stmt->execute(['symbol' => $symbol, 'user' => $user]);

        return $stmt->rowCount() > 0;
    }

    /**
     * Get total portfolio value using latest prices.
     *
     * @param string $user Username
     * @return array{total_cost: float, position_count: int}
     */
    public function getSummary(string $user = 'default'): array
    {
        $stmt = $this->db->prepare(
            'SELECT SUM(cost) / 100.0 AS total_cost, COUNT(*) AS position_count
             FROM portfolio
             WHERE user = :user'
        );
        $stmt->execute(['user' => $user]);
        $result = $stmt->fetch();

        return [
            'total_cost' => (float) ($result['total_cost'] ?? 0),
            'position_count' => (int) ($result['position_count'] ?? 0),
        ];
    }

    /**
     * Get all distinct users who have positions.
     *
     * @return array<int, string>
     */
    public function getUsers(): array
    {
        $stmt = $this->db->query(
            'SELECT DISTINCT user FROM portfolio ORDER BY user'
        );

        return array_column($stmt->fetchAll(), 'user');
    }
}

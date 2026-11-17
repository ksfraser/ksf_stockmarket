<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Model;

use PDO;

/**
 * Stock model — company metadata + latest price + scoring.
 *
 * Provides a single interface to fetch stock details combining
 * stockinfo, evalsummary, daily_tier2, and latest price.
 */
class Stock
{
    private PDO $db;

    public function __construct()
    {
        $this->db = Database::getConnection();
    }

    /**
     * Get stock info by symbol.
     */
    public function getBySymbol(string $symbol): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM stockinfo WHERE stocksymbol = :s');
        $stmt->execute(['s' => strtoupper($symbol)]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Get all active stocks.
     */
    public function getAll(): array
    {
        return $this->db->query('SELECT * FROM stockinfo ORDER BY stocksymbol')->fetchAll();
    }

    /**
     * Search stocks by name or symbol.
     */
    public function search(string $query): array
    {
        $q = '%' . strtoupper($query) . '%';
        $stmt = $this->db->prepare(
            'SELECT * FROM stockinfo
             WHERE stocksymbol LIKE :q OR corporatename LIKE :q
             ORDER BY stocksymbol
             LIMIT 50'
        );
        $stmt->execute(['q' => $q]);
        return $stmt->fetchAll();
    }

    /**
     * Get the latest stock analysis view data.
     * This uses the v_stock_analysis view that joins all indicators.
     */
    public function getAnalysis(string $symbol, ?string $date = null): ?array
    {
        $sql = 'SELECT * FROM v_stock_analysis WHERE symbol = :s';
        $params = ['s' => strtoupper($symbol)];

        if ($date) {
            $sql .= ' AND price_date = :d';
            $params['d'] = $date;
        } else {
            $sql .= ' ORDER BY price_date DESC LIMIT 1';
        }

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetch() ?: null;
    }

    /**
     * Get the composite evaluation summary.
     */
    public function getEvalSummary(string $symbol): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM evalsummary WHERE symbol = :s');
        $stmt->execute(['s' => strtoupper($symbol)]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Get price history.
     */
    public function getPriceHistory(string $symbol, int $days = 250): array
    {
        $stmt = $this->db->prepare(
            'SELECT * FROM stockprices
             WHERE symbol = :s AND price_date >= DATE_SUB(CURDATE(), INTERVAL %d DAY)
             ORDER BY price_date ASC'
        );
        $stmt->execute(['s' => strtoupper($symbol)]);
        return $stmt->fetchAll();
    }
}

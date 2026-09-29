<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Model;

use PDO;

/**
 * Scoring model — read and write investment thesis scores.
 *
 * Works with all 10 scoring tables from the modernized schema.
 */
class Scoring
{
    private PDO $db;

    public function __construct()
    {
        $this->db = Database::getConnection();
    }

    /**
     * Get the full scoring dashboard for a symbol.
     * Combines all 10 scoring tables into a single array.
     */
    public function getFullScorecard(string $symbol): array
    {
        $symbol = strtoupper($symbol);
        $tables = [
            'evalsummary', 'motleyfool', 'investorplace', 'tenets',
            'evalbusiness', 'ratios', 'evalmanagement', 'evalmarket', 'evalvalue',
        ];

        $scorecard = ['symbol' => $symbol];

        foreach ($tables as $table) {
            $stmt = $this->db->prepare("SELECT * FROM {$table} WHERE symbol = :s");
            $stmt->execute(['s' => $symbol]);
            $row = $stmt->fetch();
            if ($row) {
                unset($row['id'], $row['symbol']);
                $scorecard[$table] = $row;
            }
        }

        return $scorecard;
    }

    /**
     * Get the composite total score.
     */
    public function getTotalScore(string $symbol): ?array
    {
        $stmt = $this->db->prepare(
            'SELECT totalscore, llm_recommendation, human_recommendation, human_notes
             FROM evalsummary WHERE symbol = :s'
        );
        $stmt->execute(['s' => strtoupper($symbol)]);
        return $stmt->fetch() ?: null;
    }

    /**
     * Update a score with human override.
     */
    public function humanOverride(string $symbol, string $table, array $fields,
                                    string $notes = ''): bool
    {
        $symbol = strtoupper($symbol);
        $allowedTables = [
            'evalsummary', 'motleyfool', 'investorplace', 'tenets',
            'evalbusiness', 'evalmanagement', 'evalmarket', 'evalvalue',
        ];

        if (!in_array($table, $allowedTables, true)) {
            return false;
        }

        $fields['human_overridden'] = 1;
        $fields['updated_at'] = date('Y-m-d H:i:s');

        if ($table === 'evalsummary' && $notes) {
            $fields['human_notes'] = $notes;
        }

        $setClause = implode(', ', array_map(fn($f) => "{$f} = :{$f}", array_keys($fields)));
        $fields['symbol'] = $symbol;

        $stmt = $this->db->prepare("UPDATE {$table} SET {$setClause} WHERE symbol = :symbol");
        return $stmt->execute($fields);
    }

    /**
     * Get symbols ranked by composite score.
     */
    public function getRanked(int $limit = 50, ?int $minScore = null): array
    {
        $sql = 'SELECT symbol, totalscore, llm_recommendation, human_recommendation
                FROM evalsummary WHERE 1=1';
        $params = [];

        if ($minScore !== null) {
            $sql .= ' AND totalscore >= :min';
            $params['min'] = $minScore;
        }

        $sql .= ' ORDER BY totalscore DESC LIMIT :lim';
        $params['lim'] = $limit;

        $stmt = $this->db->prepare($sql);
        foreach ($params as $key => $val) {
            $stmt->bindValue($key, $val, is_int($val) ? PDO::PARAM_INT : PDO::PARAM_STR);
        }
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /**
     * Get symbols filtered by recommendation.
     */
    public function getByRecommendation(string $rec, string $source = 'human', int $limit = 50): array
    {
        $col = $source === 'llm' ? 'llm_recommendation' : 'human_recommendation';
        $stmt = $this->db->prepare(
            "SELECT symbol, totalscore, {$col} as recommendation
             FROM evalsummary WHERE {$col} = :rec ORDER BY totalscore DESC LIMIT :lim"
        );
        $stmt->bindValue('rec', $rec);
        $stmt->bindValue('lim', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /**
     * Get scoring history for a symbol.
     */
    public function getHistory(string $symbol, int $limit = 50): array
    {
        $stmt = $this->db->prepare(
            'SELECT * FROM scoring_history
             WHERE symbol = :s ORDER BY scored_at DESC, id DESC LIMIT :lim'
        );
        $stmt->bindValue('s', strtoupper($symbol));
        $stmt->bindValue('lim', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }
}

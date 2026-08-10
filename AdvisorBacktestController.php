<?php
declare(strict_types=1);

class AdvisorBacktestController
{
    public function leaderboard(): array
    {
        $pdo = Database::get();
        $stmt = $pdo->query("
            SELECT r.id AS run_id, r.user_id, r.strategy, r.start_date, r.end_date, r.initial_capital, r.final_value,
                   r.total_return, r.annualized_return, r.max_drawdown, r.num_trades, r.win_rate,
                   u.username AS slug, u.display_name
            FROM backtest_runs r
            LEFT JOIN users u ON u.id = r.user_id AND u.role = 'advisor'
            WHERE r.strategy LIKE '%:%' OR r.user_id IN (SELECT id FROM users WHERE role='advisor')
            ORDER BY r.final_value DESC
        ");
        $advisors = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Parse strategy string like "buffett_quality:warren-buffet:Warren Buffett"
        foreach ($advisors as &$a) {
            $parts = explode(':', (string)($a['strategy'] ?? ''), 3);
            $a['strategy'] = $parts[0] ?? '';
            $a['slug'] = $a['slug'] ?? ($parts[1] ?? 'unknown');
            $a['display_name'] = $a['display_name'] ?? ($parts[2] ?? $a['slug']);
        }

        return [
            'pageTitle' => 'Advisor Backtest Performance',
            'template' => 'advisor_backtest',
            'summary' => [
                'generated_at' => date('Y-m-d H:i'),
                'start' => $advisors[0]['start_date'] ?? '2022-01-01',
                'end' => $advisors[0]['end_date'] ?? date('Y-m-d'),
                'initial_capital' => $advisors[0]['initial_capital'] ?? 100000,
                'advisors' => $advisors,
            ],
        ];
    }

    public function trades(int $runId): array
    {
        $run = [];
        $trades = [];
        if ($runId > 0) {
            $pdo = Database::get();
            $stmt = $pdo->prepare('SELECT * FROM backtest_runs WHERE id = :id LIMIT 1');
            $stmt->execute([':id' => $runId]);
            $run = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];

            $stmt = $pdo->prepare('SELECT * FROM backtest_trades WHERE backtest_id = :bid ORDER BY trade_date ASC, id ASC');
            $stmt->execute([':bid' => $runId]);
            $trades = $stmt->fetchAll(PDO::FETCH_ASSOC);
        }

        return [
            'pageTitle' => 'Advisor Backtest Trades',
            'template' => 'advisor_backtest_trades',
            'run' => $run,
            'trades' => $trades,
        ];
    }
}

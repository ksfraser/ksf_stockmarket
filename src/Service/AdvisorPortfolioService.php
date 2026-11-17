<?php
declare(strict_types=1);

namespace ksfraser\StockMarket\Service;

use ksfraser\StockMarket\Model\Database;

/**
 * AdvisorPortfolioService — generate portfolio targets from hired advisors'
 * linked screens and strategy rules.
 */
class AdvisorPortfolioService
{
    private PDO $pdo;

    public function __construct()
    {
        $this->pdo = Database::get();
    }

    /**
     * Generate portfolio targets for all active advisors for a given user.
     *
     * @return array{generated:int, skipped:int, errors:array<int,string>}
     */
    public function generateForUser(int $userId): array
    {
        // Load hired advisors with their config
        $stmt = $this->pdo->prepare("
            SELECT ua.id AS user_advisor_id, ua.advisor_id, ua.linked_screen_ids,
                   ua.strategy_rules, ua.money_management,
                   a.display_name, a.slug
            FROM user_advisors ua
            JOIN advisor_accounts a ON a.id = ua.advisor_id
            WHERE ua.user_id = :uid AND ua.is_active = 1
        ");
        $stmt->execute([':uid' => $userId]);
        $advisors = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $generated = 0;
        $skipped = 0;
        $errors = [];

        foreach ($advisors as $adv) {
            try {
                $count = $this->generateForAdvisor((int)$adv['user_advisor_id'], $adv);
                $generated += $count;
            } catch (\Throwable $e) {
                $skipped++;
                $errors[] = $adv['display_name'] . ': ' . $e->getMessage();
            }
        }

        return [
            'generated' => $generated,
            'skipped' => $skipped,
            'errors' => $errors,
        ];
    }

    /**
     * Generate portfolio targets for a single hired advisor row.
     *
     * @return int Number of target rows written
     */
    private function generateForAdvisor(int $userAdvisorId, array $adv): int
    {
        $screenIds = [];
        if (!empty($adv['linked_screen_ids'])) {
            foreach (explode(',', (string)$adv['linked_screen_ids']) as $sid) {
                $sid = (int)trim($sid);
                if ($sid > 0) {
                    $screenIds[] = $sid;
                }
            }
        }

        if (!$screenIds) {
            return 0;
        }

        // Build preset names for these screens
        $stmt = $this->pdo->prepare("
            SELECT id, name FROM user_screens
            WHERE id IN (" . implode(',', array_fill(0, count($screenIds), '?')) . ")
        ");
        $stmt->execute($screenIds);
        $screens = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $presetNames = [];
        foreach ($screens as $s) {
            $slug = preg_replace('/[^a-z0-9_]/i', '_', (string)($s['name'] ?? 'unknown'));
            $presetNames[] = 'rw_screen_' . (int)$s['id'] . '_' . $slug;
        }

        if (!$presetNames) {
            return 0;
        }

        // Load latest results for these screens
        $in = implode(',', array_fill(0, count($presetNames), '?'));
        $stmt = $this->pdo->prepare("
            SELECT symbol, data, run_at, preset_name
            FROM tradingview_screener_results
            WHERE preset_name IN ($in)
            AND run_at = (
                SELECT MAX(run_at) FROM tradingview_screener_results t2
                WHERE t2.preset_name = tradingview_screener_results.preset_name
            )
        ");
        $stmt->execute($presetNames);
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

        if (!$rows) {
            return 0;
        }

        // Deduplicate by symbol across screens
        $bySymbol = [];
        foreach ($rows as $r) {
            $sym = $r['symbol'];
            if (!isset($bySymbol[$sym])) {
                $bySymbol[$sym] = [
                    'symbol' => $sym,
                    'count' => 0,
                    'data' => $r['data'],
                    'run_at' => $r['run_at'],
                ];
            }
            $bySymbol[$sym]['count']++;
        }

        // Simple weighting: equal weight among all unique symbols
        $symbols = array_values($bySymbol);
        $count = count($symbols);
        if ($count === 0) {
            return 0;
        }
        $weight = round(100.0 / $count, 4);

        // Parse money management settings
        $moneyRules = [];
        if (!empty($adv['money_management'])) {
            $parsed = json_decode((string)$adv['money_management'], true);
            if (is_array($parsed)) {
                $moneyRules = $parsed;
            }
        }

        // Determine risk parameters from money management selection
        $stopLossPct = 0.15;      // default 15%
        $atrMultiplier = 2.0;     // default 2x ATR
        foreach ($moneyRules as $rule) {
            if ($rule === 'ATR Trailing Stop') {
                $atrMultiplier = 2.0;
            }
            if ($rule === 'Kelly Criterion Position Sizing') {
                // Kelly caps are handled at trade time; here we just note it
            }
        }

        // Remove old targets for this advisor
        $this->pdo->prepare('DELETE FROM layer3_portfolios WHERE backtest_id = :bid')
            ->execute([':bid' => $userAdvisorId]);

        // Insert new targets
        $insert = $this->pdo->prepare('
            INSERT INTO layer3_portfolios (backtest_id, symbol, target_weight, current_weight)
            VALUES (:bid, :sym, :tw, :cw)
        ');
        foreach ($symbols as $row) {
            $insert->execute([
                ':bid' => $userAdvisorId,
                ':sym' => $row['symbol'],
                ':tw' => $weight,
                ':cw' => 0.0,
            ]);
        }

        return $count;
    }
}

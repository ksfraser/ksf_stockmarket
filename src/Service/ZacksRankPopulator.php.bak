<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Service;

use PDO;

/**
 * Populates fundamentals.zacks_rank/zacks_composite/zacks_*_grade for the
 * latest row per active symbol.
 *
 * The columns exist in the schema (added by zacks_scraper) but are currently
 * 0% populated. Research Wizard screens frequently filter "Zacks Rank = 1"
 * (field code 192), so the rank must be computed before those screens can run.
 *
 * Scoring mirrors the spirit of StockController::calcZacksStyleScore() (the
 * Zacks-style VGM composite) but is self-contained: Value/Growth come from
 * stored fundamentals, Momentum from computed price windows instead of
 * intraday RSI/SMA. Kept column-stable so it can be replaced by a genuine
 * nightly fetch of Zacks Rank later without schema changes.
 */
final class ZacksRankPopulator
{
    public function __construct(private PDO $pdo)
    {
    }

    /**
     * @return array{updated_rank:int,scored:int,total_active:int,distribution:array<int,int>}
     */
    public function populateAll(): array
    {
        $universe = new ZacksUniverse($this->pdo);
        $universe->load();

        // First pass: compute composite + grades for every symbol with data.
        $scores = [];
        foreach ($universe->rows() as $row) {
            $fund = $row['fund'] ?? null;
            if ($fund === null || empty($fund['id'])) {
                continue;
            }
            $s = self::scoreFor($fund, $row['win'] ?? [], $row['price']['close'] ?? null);
            if ($s === null) {
                continue;
            }
            $scores[] = ['id' => (int) $fund['id'], 'symbol' => $row['symbol']] + $s;
        }

        $total = count($scores);
        if ($total === 0) {
            return ['updated_rank' => 0, 'scored' => 0, 'total_active' => 0, 'distribution' => []];
        }

        // Rank = percentile band over the scored universe (Zacks-like spread).
        $sorted = array_column($scores, 'composite');
        rsort($sorted);
        $ranks = [];
        foreach ($scores as $i => $s) {
            $pos = $this->percentilePosition($s['composite'], $sorted);
            $ranks[$i] = self::rankForPercentile($pos);
        }
        $distribution = array_count_values($ranks);
        ksort($distribution);

        $stmt = $this->pdo->prepare(
            "UPDATE fundamentals
             SET zacks_rank = ?, zacks_rank_text = ?, zacks_composite = ?,
                 zacks_value_grade = ?, zacks_growth_grade = ?,
                 zacks_momentum_grade = ?, zacks_vgm_grade = ?
             WHERE id = ?"
        );

        $updated = 0;
        foreach ($scores as $i => $s) {
            $rank = $ranks[$i];
            $ok = $stmt->execute([
                $rank,
                self::rankText($rank),
                $s['composite'],
                $s['value_grade'],
                $s['growth_grade'],
                $s['momentum_grade'],
                $s['vgm_grade'],
                $s['id'],
            ]);
            if ($ok) {
                $updated++;
            }
        }

        return [
            'updated_rank' => $updated,
            'scored' => $total,
            'total_active' => $universe->count(),
            'distribution' => $distribution,
        ];
    }

    private function percentilePosition(float $value, array $sortedDesc): float
    {
        $n = count($sortedDesc);
        if ($n === 0) {
            return 0.0;
        }
        // Fraction of the universe with a composite score >= this one.
        $atOrAbove = 0;
        foreach ($sortedDesc as $v) {
            if ($v >= $value) {
                $atOrAbove++;
            }
        }
        return $atOrAbove / $n;
    }

    /**
     * Map a composite percentile to a Zacks-like 1-5 rank:
     * top 5% -> 1, next 25% -> 2, middle 40% -> 3, next 25% -> 4, bottom 5% -> 5.
     * (Approximation of Zacks' published rank distribution, since a genuine
     * Zacks Rank feed is not available in this DB yet.)
     */
    public static function rankForPercentile(float $pct): int
    {
        if ($pct >= 0.95) return 1;
        if ($pct >= 0.70) return 2;
        if ($pct >= 0.30) return 3;
        if ($pct >= 0.05) return 4;
        return 5;
    }

    public static function rankText(int $rank): string
    {
        return match ($rank) {
            1 => 'Strong Buy',
            2 => 'Buy',
            3 => 'Hold',
            4 => 'Sell',
            default => 'Strong Sell',
        };
    }

    /**
     * @param array<string,mixed> $f    latest fundamentals row
     * @param array<string,mixed> $win  computed price windows
     * @return array<string,mixed>|null
     */
    public static function scoreFor(array $f, array $win, mixed $closePrice): ?array
    {
        $hasData = false;
        foreach (['trailing_pe', 'price_to_book', 'free_cash_flow', 'market_cap',
                  'debt_to_equity', 'earnings_growth', 'revenue_growth', 'roe'] as $k) {
            if (isset($f[$k]) && $f[$k] !== null && $f[$k] !== '') {
                $hasData = true;
                break;
            }
        }
        if (!$hasData || $closePrice === null) {
            return null;
        }

        // Value (40): low PE, low PB, FCF yield, manageable debt.
        $valueScore = 0;
        $maxValue = 0;
        if (!empty($f['trailing_pe']) && $f['trailing_pe'] > 0) {
            $maxValue += 10;
            $pe = (float) $f['trailing_pe'];
            if ($pe < 15) $valueScore += 10;
            elseif ($pe < 20) $valueScore += 7;
            elseif ($pe < 30) $valueScore += 4;
        }
        if (!empty($f['price_to_book']) && $f['price_to_book'] > 0) {
            $maxValue += 10;
            $pb = (float) $f['price_to_book'];
            if ($pb < 1.0) $valueScore += 10;
            elseif ($pb < 2.0) $valueScore += 7;
            elseif ($pb < 3.0) $valueScore += 4;
        }
        if (!empty($f['free_cash_flow']) && !empty($f['market_cap']) && $f['market_cap'] > 0) {
            $maxValue += 10;
            $fcfYield = (float) $f['free_cash_flow'] / (float) $f['market_cap'];
            if ($fcfYield > 0.06) $valueScore += 10;
            elseif ($fcfYield > 0.03) $valueScore += 7;
            elseif ($fcfYield > 0.01) $valueScore += 4;
        }
        if (!empty($f['debt_to_equity'])) {
            $maxValue += 10;
            $de = (float) $f['debt_to_equity'];
            if ($de < 0.3) $valueScore += 10;
            elseif ($de < 0.8) $valueScore += 7;
            elseif ($de < 1.5) $valueScore += 4;
        }
        $valuePct = $maxValue > 0 ? min(100, ($valueScore / $maxValue) * 100) : 0;

        // Growth (30): trailing EPS growth, revenue growth.
        $growthScore = 0;
        $maxGrowth = 0;
        if (!empty($f['earnings_growth'])) {
            $maxGrowth += 15;
            $eg = (float) $f['earnings_growth'];
            if ($eg > 0.20) $growthScore += 15;
            elseif ($eg > 0.10) $growthScore += 10;
            elseif ($eg > 0) $growthScore += 5;
        }
        if (!empty($f['revenue_growth'])) {
            $maxGrowth += 15;
            $rg = (float) $f['revenue_growth'];
            if ($rg > 0.15) $growthScore += 15;
            elseif ($rg > 0.05) $growthScore += 10;
            elseif ($rg > 0) $growthScore += 5;
        }
        $growthPct = $maxGrowth > 0 ? min(100, ($growthScore / $maxGrowth) * 100) : 0;

        // Momentum (20): price vs 52W high + trailing 4W change.
        $momentumScore = 0;
        $vsHigh = $win['chg_vs_high_52w'] ?? null;
        if ($vsHigh !== null) {
            if ($vsHigh >= 95) $momentumScore += 10;
            elseif ($vsHigh >= 85) $momentumScore += 8;
            elseif ($vsHigh >= 70) $momentumScore += 5;
            elseif ($vsHigh >= 50) $momentumScore += 2;
        }
        $chg4 = $win['chg_4w'] ?? null;
        if ($chg4 !== null) {
            if ($chg4 > 10) $momentumScore += 10;
            elseif ($chg4 > 5) $momentumScore += 8;
            elseif ($chg4 > 0) $momentumScore += 5;
            elseif ($chg4 > -5) $momentumScore += 2;
        }
        $momentumPct = min(100, $momentumScore / 20 * 100);

        $vgmPct = ($valuePct + $growthPct + $momentumPct) / 3;
        $composite = $valuePct * 0.40 + $growthPct * 0.30 + $momentumPct * 0.20 + $vgmPct * 0.10;

        return [
            'composite' => round($composite, 1),
            'value_grade' => self::grade($valuePct),
            'growth_grade' => self::grade($growthPct),
            'momentum_grade' => self::grade($momentumPct),
            'vgm_grade' => self::grade($vgmPct),
        ];
    }

    private static function grade(float $pct): string
    {
        if ($pct >= 90) return 'A';
        if ($pct >= 80) return 'B';
        if ($pct >= 70) return 'C';
        if ($pct >= 60) return 'D';
        return 'F';
    }
}
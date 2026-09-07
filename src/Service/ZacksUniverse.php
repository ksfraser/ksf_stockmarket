<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Service;

use PDO;

/**
 * Materializes the live-data universe the Zacks RW runner evaluates against.
 *
 * One row per active symbol, assembled from:
 *   base   — symbol_master (name/exchange/sector/industry/...)
 *   price  — latest stockprices row (close/volume/price_date)
 *   fund   — latest fundamentals row (zacks_* + ratios)
 *   win    — computed price windows (1W/4W/12W/24W/52W/YTD changes, 52W H/L,
 *            position-in-range, price vs 52W high)
 *   vol20  — 20-trading-day average volume (only when a rule needs it)
 *
 * Windows are anchored to the universe-wide latest price date, matching how
 * Research Wizard evaluates a screen against "today".
 */
final class ZacksUniverse
{
    private const WINDOW_WEEKS = ['1w' => 1, '4w' => 4, '12w' => 12, '24w' => 24, '52w' => 52];

    private PDO $pdo;

    /** @var array<string,array{
     *     symbol:string, base:?array, price:?array, fund:?array, win:?array, vol20:?float
     * }>
     */
    private array $rows = [];

    private ?string $anchorDate = null;

    private bool $needVol20 = false;

    public function __construct(PDO $pdo)
    {
        $this->pdo = $pdo;
    }

    public function setNeedVol20(bool $need): void
    {
        $this->needVol20 = $need;
    }

    public function anchorDate(): ?string
    {
        return $this->anchorDate;
    }

    /** @return array<string,array> */
    public function rows(): array
    {
        return $this->rows;
    }

    public function count(): int
    {
        return count($this->rows);
    }

    public function load(): void
    {
        $this->anchorDate = (string) $this->pdo->query(
            "SELECT MAX(price_date) FROM stockprices"
        )->fetchColumn();

        $this->loadBase();
        $this->loadPrices();
        $this->loadFundamentals();
        $this->loadWindows();
        if ($this->needVol20) {
            $this->loadVol20();
        }
    }

    private function loadBase(): void
    {
        $stmt = $this->pdo->query(
            "SELECT symbol, name, exchange, sector, industry, currency, geography
             FROM symbol_master WHERE is_active = 1"
        );
        foreach ($stmt as $r) {
            $sym = (string) $r['symbol'];
            $this->rows[$sym]['symbol'] = $sym;
            $this->rows[$sym]['base'] = $r;
            $this->rows[$sym]['price'] = null;
            $this->rows[$sym]['fund'] = null;
            $this->rows[$sym]['win'] = null;
            $this->rows[$sym]['vol20'] = null;
        }
    }

    private function loadPrices(): void
    {
        $stmt = $this->pdo->query(
            "SELECT sp.symbol, sp.price_date, sp.close, sp.volume
             FROM stockprices sp
             JOIN (SELECT symbol, MAX(price_date) md FROM stockprices GROUP BY symbol) g
               ON g.symbol = sp.symbol AND sp.price_date = g.md"
        );
        foreach ($stmt as $r) {
            $sym = (string) $r['symbol'];
            if (!isset($this->rows[$sym])) {
                continue;
            }
            $this->rows[$sym]['price'] = $r;
        }
    }

    private function loadFundamentals(): void
    {
        $stmt = $this->pdo->query(
            "SELECT f.*
             FROM fundamentals f
             JOIN (SELECT symbol, MAX(fetch_date) md FROM fundamentals GROUP BY symbol) g
               ON g.symbol = f.symbol AND f.fetch_date = g.md"
        );
        foreach ($stmt as $r) {
            $sym = (string) $r['symbol'];
            if (!isset($this->rows[$sym])) {
                continue;
            }
            $this->rows[$sym]['fund'] = $r;
        }
    }

    private function loadWindows(): void
    {
        $anchor = $this->anchorDate;
        if ($anchor === null) {
            return;
        }

        // Historical close at each offset (closest price_date <= anchor - W).
        $offsets = [];
        foreach (self::WINDOW_WEEKS as $key => $weeks) {
            $offsets[$key] = $this->closePerSymbolAtOffset($anchor, $weeks);
        }
        // YTD anchor: first price_date of the calendar year.
        $ytd = $this->closeAtYearStart($anchor);
        // 52-week high/low.
        $hl = $this->highLow52w($anchor);

        foreach ($this->rows as $sym => &$row) {
            $price = $row['price'];
            if ($price === null || !isset($price['close']) || $price['close'] === null) {
                continue;
            }
            $close = (float) $price['close'];
            $win = [];
            foreach (self::WINDOW_WEEKS as $key => $weeks) {
                $past = $offsets[$key][$sym] ?? null;
                $win['chg_' . $key] = ($past !== null && $past > 0)
                    ? ($close - $past) / $past * 100.0
                    : null;
            }
            $yearOpen = $ytd[$sym] ?? null;
            $win['chg_ytd'] = ($yearOpen !== null && $yearOpen > 0)
                ? ($close - $yearOpen) / $yearOpen * 100.0
                : null;

            $high = $hl[$sym]['high'] ?? null;
            $low = $hl[$sym]['low'] ?? null;
            $win['high_52w'] = $high !== null ? (float) $high : null;
            $win['low_52w'] = $low !== null ? (float) $low : null;
            $win['hl_range_pct'] = ($high !== null && $low !== null && $high > $low)
                ? ($close - (float) $low) / ((float) $high - (float) $low) * 100.0
                : null;
            $win['chg_vs_high_52w'] = ($high !== null && (float) $high > 0)
                ? $close / (float) $high * 100.0
                : null;

            $row['win'] = $win;
        }
        unset($row);
    }

    private function loadVol20(): void
    {
        $anchor = $this->anchorDate;
        if ($anchor === null) {
            return;
        }
        $from = date('Y-m-d', strtotime($anchor . ' - 45 days'));
        $stmt = $this->pdo->prepare(
            "SELECT symbol, AVG(volume) avg_vol
             FROM (
                 SELECT symbol, volume,
                        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY price_date DESC) rn
                 FROM stockprices
                 WHERE price_date >= ?
             ) t
             WHERE rn <= 20
             GROUP BY symbol"
        );
        $stmt->execute([$from]);
        foreach ($stmt as $r) {
            $sym = (string) $r['symbol'];
            if (isset($this->rows[$sym])) {
                $this->rows[$sym]['vol20'] = $r['avg_vol'] !== null ? (float) $r['avg_vol'] : null;
            }
        }
    }

    /** @return array<string,float> */
    private function closePerSymbolAtOffset(string $anchor, int $weeks): array
    {
        $cutoff = date('Y-m-d', strtotime($anchor . " - {$weeks} weeks"));
        $stmt = $this->pdo->prepare(
            "SELECT s2.symbol, s2.close
             FROM stockprices s2
             JOIN (SELECT symbol, MAX(price_date) md
                   FROM stockprices WHERE price_date <= ? GROUP BY symbol) g
               ON g.symbol = s2.symbol AND s2.price_date = g.md"
        );
        $stmt->execute([$cutoff]);
        $out = [];
        foreach ($stmt as $r) {
            if ($r['close'] !== null) {
                $out[$r['symbol']] = (float) $r['close'];
            }
        }
        return $out;
    }

    /** @return array<string,float> */
    private function closeAtYearStart(string $anchor): array
    {
        $year = substr($anchor, 0, 4);
        $stmt = $this->pdo->prepare(
            "SELECT s2.symbol, s2.close
             FROM stockprices s2
             JOIN (SELECT symbol, MIN(price_date) md
                   FROM stockprices WHERE price_date >= ? GROUP BY symbol) g
               ON g.symbol = s2.symbol AND s2.price_date = g.md"
        );
        $stmt->execute([$year . '-01-01']);
        $out = [];
        foreach ($stmt as $r) {
            if ($r['close'] !== null) {
                $out[$r['symbol']] = (float) $r['close'];
            }
        }
        return $out;
    }

    /** @return array<string,array{high:?float,low:?float}> */
    private function highLow52w(string $anchor): array
    {
        $from = date('Y-m-d', strtotime($anchor . ' - 52 weeks'));
        $stmt = $this->pdo->prepare(
            "SELECT symbol, MAX(close) high, MIN(close) low
             FROM stockprices WHERE price_date >= ? GROUP BY symbol"
        );
        $stmt->execute([$from]);
        $out = [];
        foreach ($stmt as $r) {
            $out[$r['symbol']] = [
                'high' => $r['high'] !== null ? (float) $r['high'] : null,
                'low'  => $r['low'] !== null ? (float) $r['low'] : null,
            ];
        }
        return $out;
    }
}
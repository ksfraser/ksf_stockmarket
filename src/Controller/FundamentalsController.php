<?php
/**
 * FundamentalsController — handles fundamental data display.
 */
class FundamentalsController {
    private $pdo;

    public function __construct() {
        $this->pdo = Database::get();
    }

    /**
     * Get latest fundamental data for a symbol.
     * Tries .TO suffix for Canadian symbols if no direct match.
     */
    public function getSymbol(string $symbol): array {
        $stmt = $this->pdo->prepare("
            SELECT * FROM fundamentals
            WHERE symbol = :sym
            ORDER BY fetch_date DESC LIMIT 1
        ");
        $stmt->execute([':sym' => $symbol]);
        $result = $stmt->fetch();
        
        // If no match, try .TO suffix for Canadian symbols (only if symbol doesn't already have it)
        if (!$result && preg_match('/^[A-Z]/', $symbol) && !str_ends_with($symbol, '.TO')) {
            $stmt = $this->pdo->prepare("
                SELECT * FROM fundamentals
                WHERE symbol = :sym
                ORDER BY fetch_date DESC LIMIT 1
            ");
            $stmt->execute([':sym' => $symbol . '.TO']);
            $result = $stmt->fetch();
        }
        return $result ?: [];
    }

    /**
     * Get dividend safety score.
     */
    public function getDividendSafety(string $symbol): array {
        $f = $this->getSymbol($symbol);

        if (!$f) {
            return ['score' => null, 'rating' => 'NO DATA', 'components' => []];
        }

        $score = 100;
        $components = [];

        // Payout ratio
        if ($f['payout_ratio'] !== null) {
            $pr = (float)$f['payout_ratio'];
            if ($pr > 1.0) { $score -= 40; $components[] = ['Payout Ratio', 'CRITICAL', sprintf('%.0f%% — exceeds earnings', $pr * 100)]; }
            elseif ($pr > 0.8) { $score -= 20; $components[] = ['Payout Ratio', 'WARNING', sprintf('%.0f%% — limited cushion', $pr * 100)]; }
            elseif ($pr > 0.6) { $score -= 10; $components[] = ['Payout Ratio', 'CAUTION', sprintf('%.0f%%', $pr * 100)]; }
            else { $components[] = ['Payout Ratio', 'OK', sprintf('%.0f%%', $pr * 100)]; }
        }

        // FCF coverage
        if ($f['dividend_fcf_coverage'] !== null) {
            $cov = (float)$f['dividend_fcf_coverage'];
            if ($cov < 0.5) { $score -= 35; $components[] = ['FCF Coverage', 'CRITICAL', sprintf('%.1f× — not covering dividends', $cov)]; }
            elseif ($cov < 0.8) { $score -= 20; $components[] = ['FCF Coverage', 'WARNING', sprintf('%.1f×', $cov)]; }
            elseif ($cov < 1.0) { $score -= 10; $components[] = ['FCF Coverage', 'CAUTION', sprintf('%.1f×', $cov)]; }
            else { $components[] = ['FCF Coverage', 'OK', sprintf('%.1f×', $cov)]; }
        }

        // Debt/Equity
        if ($f['debt_to_equity'] !== null) {
            $de = (float)$f['debt_to_equity'];
            if ($de > 2.0) { $score -= 20; $components[] = ['Debt/Equity', 'CRITICAL', sprintf('%.1f× — highly leveraged', $de)]; }
            elseif ($de > 1.5) { $score -= 10; $components[] = ['Debt/Equity', 'WARNING', sprintf('%.1f×', $de)]; }
            else { $components[] = ['Debt/Equity', 'OK', sprintf('%.1f×', $de)]; }
        }

        // Revenue growth
        if ($f['revenue_growth'] !== null) {
            $rg = (float)$f['revenue_growth'];
            if ($rg < -0.10) { $score -= 20; $components[] = ['Revenue Growth', 'CRITICAL', sprintf('%.1f%% declining', $rg * 100)]; }
            elseif ($rg < 0) { $score -= 10; $components[] = ['Revenue Growth', 'WARNING', sprintf('%.1f%% declining', $rg * 100)]; }
            elseif ($rg > 0.10) { $components[] = ['Revenue Growth', 'STRONG', sprintf('+%.1f%%', $rg * 100)]; }
            else { $components[] = ['Revenue Growth', 'OK', sprintf('+%.1f%%', $rg * 100)]; }
        }

        // ROE
        if ($f['roe'] !== null) {
            $roe = (float)$f['roe'];
            if ($roe > 0.20) { $components[] = ['ROE', 'STRONG', sprintf('%.1f%%', $roe * 100)]; }
            elseif ($roe > 0.15) { $components[] = ['ROE', 'GOOD', sprintf('%.1f%%', $roe * 100)]; }
            elseif ($roe > 0.10) { $components[] = ['ROE', 'OK', sprintf('%.1f%%', $roe * 100)]; }
            elseif ($roe > 0) { $components[] = ['ROE', 'WEAK', sprintf('%.1f%%', $roe * 100)]; }
            else { $score -= 10; $components[] = ['ROE', 'NEGATIVE', sprintf('%.1f%%', $roe * 100)]; }
        }

        $score = max(0, min(100, $score));
        $rating = $score >= 80 ? 'SAFE' : ($score >= 60 ? 'MODERATE' : ($score >= 40 ? 'WARNING' : 'CRITICAL'));
        $ratingColor = $score >= 80 ? '#22c55e' : ($score >= 60 ? '#eab308' : ($score >= 40 ? '#f97316' : '#ef4444'));

        return [
            'symbol' => $symbol,
            'score' => $score,
            'rating' => $rating,
            'rating_color' => $ratingColor,
            'components' => $components,
            'fetch_date' => $f['fetch_date'] ?? null,
        ];
    }

    /**
     * Get dividend history for a symbol.
     * Tries .TO suffix for Canadian symbols if no direct match.
     */
    public function getDividends(string $symbol): array {
        $sql = "SELECT * FROM dividends WHERE symbol = :sym ORDER BY ex_date DESC LIMIT 50";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([':sym' => $symbol]);
        $result = $stmt->fetchAll();
        
        // If no match, try .TO suffix for Canadian symbols (only if symbol doesn't already have it)
        if (empty($result) && preg_match('/^[A-Z]/', $symbol) && !str_ends_with($symbol, '.TO')) {
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute([':sym' => $symbol . '.TO']);
            $result = $stmt->fetchAll();
        }
        return $result;
    }
}

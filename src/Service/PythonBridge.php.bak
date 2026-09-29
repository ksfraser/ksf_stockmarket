<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Service;

use RuntimeException;

/**
 * PythonBridge — HTTP client to the Python Flask API.
 *
 * PHP calls this service to delegate analysis tasks to Python:
 *   - Technical analysis (TA indicators, signals)
 *   - Screening (Motley Fool, Buffett, etc.)
 *   - Backtesting
 *   - Fundamental scoring
 *   - Correlation analysis
 *
 * The Flask API runs on localhost:5000 and is proxied through Apache mod_proxy.
 * All requests use JSON and have a timeout to prevent hanging.
 */
class PythonBridge
{
    private string $baseUrl;
    private int $timeout;
    private string $apiKey;

    public function __construct()
    {
        $this->baseUrl = $_ENV['PYTHON_API_URL'] ?? 'http://127.0.0.1:5000';
        $this->timeout = (int) ($_ENV['PYTHON_API_TIMEOUT'] ?? 30);
        $this->apiKey = $_ENV['PYTHON_API_KEY'] ?? 'dev_key_change_me';
    }

    // ─── Health Check ───────────────────────────────────────────────────────

    public function healthCheck(): array
    {
        return $this->get('/api/health');
    }

    // ─── Technical Analysis ─────────────────────────────────────────────────

    /**
     * Run technical analysis on a symbol.
     *
     * @param string $symbol Stock symbol (e.g., 'RY.TO')
     * @param array $indicators Optional list of specific indicators
     * @param string|null $fromDate Start date (YYYY-MM-DD)
     * @param string|null $toDate End date (YYYY-MM-DD)
     * @return array ['signal' => 'BUY', 'confidence' => 75.5, 'indicators' => [...], ...]
     */
    public function analyzeTa(
        string $symbol,
        array $indicators = [],
        ?string $fromDate = null,
        ?string $toDate = null
    ): array {
        return $this->post('/api/ta/analyze', [
            'symbol' => strtoupper($symbol),
            'indicators' => $indicators,
            'from_date' => $fromDate,
            'to_date' => $toDate,
        ]);
    }

    /**
     * Get TA values for a symbol on a specific date.
     * Reads from daily_tier2 + ta_values via Python.
     */
    public function getTaValues(string $symbol, string $date): array
    {
        return $this->get("/api/ta/values/{$symbol}", ['date' => $date]);
    }

    // ─── Screening ──────────────────────────────────────────────────────────

    /**
     * Run a stock/ETF screen.
     *
     * @param string $screenType motley_fool_rule_maker | motley_fool_bear | buffett | combined | etf
     * @param string $universe tsx | tsx60 | sp500 | all
     * @param float|null $minScore Minimum composite score
     * @return array Ranked list of passing symbols with scores
     */
    public function runScreen(
        string $screenType,
        string $universe = 'tsx',
        ?float $minScore = null
    ): array {
        return $this->post('/api/screen/run', [
            'screen_type' => $screenType,
            'universe' => $universe,
            'min_score' => $minScore,
        ]);
    }

    // ─── Backtesting ────────────────────────────────────────────────────────

    /**
     * Submit a backtest to the queue.
     *
     * @return array ['run_id' => 123, 'status' => 'pending']
     */
    public function submitBacktest(
        string $strategy,
        array $parameters,
        string $startDate,
        string $endDate,
        int $userId
    ): array {
        return $this->post('/api/backtest/run', [
            'strategy' => $strategy,
            'parameters' => $parameters,
            'start_date' => $startDate,
            'end_date' => $endDate,
            'user_id' => $userId,
        ]);
    }

    public function getBacktestStatus(int $runId): array
    {
        return $this->get("/api/backtest/status/{$runId}");
    }

    public function getBacktestResults(int $runId): array
    {
        return $this->get("/api/backtest/results/{$runId}");
    }

    // ─── Scoring ────────────────────────────────────────────────────────────

    /**
     * Run fundamental scoring for a symbol.
     * Python analyzes financial data and populates scoring tables.
     *
     * @return array ['symbol' => 'RY.TO', 'totalscore' => 28, 'scores' => [...]]
     */
    public function runScoring(string $symbol): array
    {
        return $this->post('/api/scoring/run', [
            'symbol' => strtoupper($symbol),
        ]);
    }

    /**
     * Run scoring for all active symbols.
     *
     * @param int|null $limit Limit number of symbols (null for all)
     * @return array ['processed' => 150, 'errors' => 2, 'duration_s' => 45]
     */
    public function runBatchScoring(?int $limit = null): array
    {
        return $this->post('/api/scoring/run_all', [
            'limit' => $limit,
        ]);
    }

    /**
     * Get the composite evaluation summary for a symbol.
     */
    public function getEvalSummary(string $symbol): array
    {
        return $this->get("/api/scoring/summary/{$symbol}");
    }

    // ─── Correlation ────────────────────────────────────────────────────────

    /**
     * Run signal correlation analysis for a symbol.
     * Updates signal_weights table with correlation data.
     */
    public function runCorrelationAnalysis(string $symbol): array
    {
        return $this->post('/api/correlation/run', [
            'symbol' => strtoupper($symbol),
        ]);
    }

    /**
     * Run correlation analysis for all symbols.
     */
    public function runBatchCorrelation(): array
    {
        return $this->post('/api/correlation/run_all', []);
    }

    /**
     * Get signal weights for a symbol.
     */
    public function getSignalWeights(string $symbol): array
    {
        return $this->get("/api/signal_weights/{$symbol}");
    }

    // ─── Data Import ────────────────────────────────────────────────────────

    /**
     * Import latest prices from yfinance.
     *
     * @param array $symbols List of symbols (empty for all active)
     * @return array ['imported' => 1500, 'errors' => 3, 'duration_s' => 120]
     */
    public function importPrices(array $symbols = []): array
    {
        return $this->post('/api/data/import', [
            'symbols' => $symbols,
            'source' => 'yfinance',
        ]);
    }

    /**
     * Get price history for a symbol.
     */
    public function getPrices(string $symbol, ?string $from = null, ?string $to = null): array
    {
        $params = [];
        if ($from) $params['from'] = $from;
        if ($to) $params['to'] = $to;
        return $this->get("/api/data/prices/{$symbol}", $params);
    }

    // ─── HTTP Helpers ───────────────────────────────────────────────────────

    private function get(string $path, array $params = []): array
    {
        $url = $this->baseUrl . $path;
        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                "X-API-Key: {$this->apiKey}",
            ],
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($response === false) {
            throw new RuntimeException("Python API connection failed: {$error}");
        }

        if ($httpCode >= 400) {
            throw new RuntimeException(
                "Python API error (HTTP {$httpCode}): {$response}"
            );
        }

        $data = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new RuntimeException('Invalid JSON from Python API');
        }

        return $data;
    }

    private function post(string $path, array $body): array
    {
        $url = $this->baseUrl . $path;

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($body),
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                "X-API-Key: {$this->apiKey}",
            ],
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($response === false) {
            throw new RuntimeException("Python API connection failed: {$error}");
        }

        if ($httpCode >= 400) {
            throw new RuntimeException(
                "Python API error (HTTP {$httpCode}): {$response}"
            );
        }

        $data = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new RuntimeException('Invalid JSON from Python API');
        }

        return $data;
    }

    /**
     * Check if the Python API is reachable.
     */
    public function isAvailable(): bool
    {
        try {
            $result = $this->get('/api/health');
            return ($result['status'] ?? '') === 'ok';
        } catch (RuntimeException) {
            return false;
        }
    }
}

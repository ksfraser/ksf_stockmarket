<?php
/**
 * SymbolResolver — centralized TSX/US ticker disambiguation for PHP.
 *
 * Rules (same intent as python/src/symbol_resolver.py):
 *  1. If symbol already has a known suffix (.TO, .UN.TO, etc.) → return as-is.
 *  2. If symbol exists in exchange_mapping with yahoo_ticker → return that.
 *  3. If symbol_master says exchange = TSX/TSXV → append .TO.
 *  4. If portfolio.price_symbol ends in .TO for this symbol → return price_symbol.
 *  5. Otherwise return original symbol.
 */

class SymbolResolver
{
    /** @var PDO */
    private $pdo;
    /** @var array<string,string> */
    private $cache = [];

    public function __construct(PDO $pdo)
    {
        $this->pdo = $pdo;
    }

    /**
     * Resolve DB symbol to the canonical form used for yfinance / data lookup.
     */
    public function resolve(string $symbol): string
    {
        $symbol = strtoupper(trim($symbol));

        if (isset($this->cache[$symbol])) {
            return $this->cache[$symbol];
        }

        $resolved = $symbol;

        // TSX unit/class normalization: .UN → -UN.TO, .B.TO → -B.TO, etc.
        if (str_ends_with($symbol, '.UN')) {
            $resolved = substr($symbol, 0, -3) . '-UN.TO';
        } else {
            $symbol = str_replace(['.B.TO', '.UN.TO', '.U.TO'], ['-B.TO', '-UN.TO', '-U.TO'], $symbol);

            // Already suffixed
            if (!preg_match('/\.(TO|V|X|O)$/i', $symbol)) {
                // exchange_mapping yahoo_ticker
                $row = $this->fetchOne(
                    "SELECT yahoo_ticker FROM exchange_mapping WHERE symbol = :sym AND is_primary = 1 AND is_active = 1 LIMIT 1",
                    [':sym' => $symbol]
                );
                if (!empty($row['yahoo_ticker'])) {
                    $resolved = strtoupper($row['yahoo_ticker']);
                } else {
                    // portfolio.price_symbol ending in .TO
                    $row = $this->fetchOne(
                        "SELECT price_symbol FROM portfolio WHERE symbol = :sym AND price_symbol LIKE :pat LIMIT 1",
                        [':sym' => $symbol, ':pat' => $symbol . '.TO']
                    );
                    if (!empty($row['price_symbol'])) {
                        $resolved = strtoupper($row['price_symbol']);
                    } else {
                        // symbol_master exchange hints TSX/TSXV
                        $row = $this->fetchOne(
                            "SELECT exchange FROM symbol_master WHERE symbol = :sym LIMIT 1",
                            [':sym' => $symbol]
                        );
                        if (!empty($row['exchange'])) {
                            $ex = strtoupper($row['exchange']);
                            if (str_contains($ex, 'TSX') || str_contains($ex, 'TSXV')) {
                                $resolved = $symbol . '.TO';
                            }
                        }
                    }
                }
            } else {
                $resolved = $symbol;
            }
        }

        $this->cache[$symbol] = $resolved;
        return $resolved;
    }

    /**
     * Resolve AND validate: returns a list of candidate symbols to try in DB.
     * Guarantees that the original symbol is first (so existing DB data is found).
     */
    public function candidates(string $symbol): array
    {
        $resolved = $this->resolve($symbol);
        if ($resolved === $symbol) {
            return [$symbol];
        }
        return [$symbol, $resolved];
    }

    private function fetchOne(string $sql, array $params): ?array
    {
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        return $row ?: null;
    }
}

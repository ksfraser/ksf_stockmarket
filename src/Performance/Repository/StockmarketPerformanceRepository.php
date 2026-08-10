<?php
declare(strict_types=1);

namespace App\Performance\Repository;

use App\Database;
use KSF\Performance\Contracts\TransactionInterface;
use KSF\Performance\Contracts\TransactionRepositoryInterface;
use KSF\Performance\Contracts\ValuationInterface;
use KSF\Performance\DTO\ValuationDTO;

/**
 * Maps stockmarket DB tables → portfolio-math interfaces.
 *
 * portfolioId = account_type in the stockmarket schema
 *              ('TFSA', 'RRSP', 'MARGIN', etc.)
 */
class StockmarketPerformanceRepository implements TransactionRepositoryInterface
{
    private \PDO $pdo;
    private ?int $userId = null;

    public function __construct()
    {
        $this->pdo = Database::get();
    }

    public function setUserId(int $userId): void
    {
        $this->userId = $userId;
    }

    public function findByPortfolioAndRange(string $portfolioId, \DateTimeInterface $start, \DateTimeInterface $end): array
    {
        $sql = "
            SELECT
                id,
                trade_date AS date,
                total AS amount,
                type,
                currency,
                symbol,
                commission,
                CASE
                    WHEN type IN ('BUY','FEE','TAX','INTEREST_CHARGE','SPLIT') THEN 'outflow'
                    WHEN type IN ('SELL','DIVIDEND','DIV-RECV','INTEREST','DEPOSIT') THEN 'inflow'
                    WHEN type IN ('WITHDRAWAL') THEN 'outflow'
                    WHEN type IN ('TRANSFER') THEN 'transfer'
                    ELSE 'other'
                END AS flow_sign
            FROM transactions
            WHERE account_type = :portfolioId
              AND trade_date BETWEEN :start AND :end
              AND is_deleted = 0
              AND total IS NOT NULL
              AND user_id = :user_id
            ORDER BY trade_date ASC, id ASC
        ";
        $stmt = $this->pdo->prepare($sql);
        // Note: :user_id param is added via execute() if set
        $params = [
            ':portfolioId'  => $portfolioId,
            ':start'        => $start->format('Y-m-d'),
            ':end'          => $end->format('Y-m-d'),
        ];
        if ($this->userId !== null) { $params[':user_id'] = $this->userId; }
        $stmt->execute($params);
        $rows = $stmt->fetchAll();

        return array_map(
            fn ($r) => new class($r) implements TransactionInterface {
                public function __construct(private array $r) {}
                public function getId(): string          { return (string) $this->r['id']; }
                public function getDate(): \DateTimeInterface { return new \DateTimeImmutable($this->r['date']); }
                public function getAmount(): float        { return (float) $this->r['amount']; }
                public function getType(): string         { return strtolower($this->r['type']); }
                public function getCurrency(): string     { return $this->r['currency'] ?: 'CAD'; }
                public function getSecurityId(): ?string  { return $this->r['symbol'] ?: null; }
                public function getFlowSign(): string     { return $this->r['flow_sign']; }
                public function getCommission(): float    { return (float) ($this->r['commission'] ?? 0.0); }
            },
            $rows
        );
    }

    public function findValuationsByPortfolioAndRange(string $portfolioId, \DateTimeInterface $start, \DateTimeInterface $end): array
    {
        // Reconstruct daily valuations from transaction cash flows + current holding prices.
        // We build a cash-and-holdings ledger day-by-day.
        $txs = $this->findByPortfolioAndRange($portfolioId, $start, $end);

        // Group transactions by date
        $byDate = [];
        foreach ($txs as $tx) {
            $ds = $tx->getDate()->format('Y-m-d');
            $byDate[$ds] = $txs; // shorthand
        }

        // Rebuild: start from most recent non-null holdings value, walk backwards
        // For TWR we need a monotonic series of portfolio values.

        // Simplest approach: use transactions + reconstructed holdings
        // 1. Get current holdings for this account
        $holdings = $this->pdo->prepare("
            SELECT symbol, shares, cost_basis, account_type
            FROM portfolio
            WHERE account_type = :portfolioId
              AND shares > 0
              AND user_id = :user_id
        ");
        $holdings->execute(($this->userId !== null ? [':portfolioId' => $portfolioId, ':user_id' => $this->userId] : [':portfolioId' => $portfolioId]));
        $currentHoldings = $holdings->fetchAll();

        // 2. Build daily closing prices for held symbols over the range
        $symbols = array_map(fn ($h) => $h['symbol'], $currentHoldings);
        $vals = [];

        if (empty($symbols)) {
            // No holdings — return empty series; caller will throw InsufficientDataException
            return [];
        }

        $inQuote = str_repeat('?', count($symbols));
        $priceStmt = $this->pdo->prepare("
            SELECT price_date, symbol, close
            FROM stockprices
            WHERE symbol IN ($inQuote)
              AND price_date BETWEEN :start AND :end
            ORDER BY price_date ASC, symbol ASC
        ");
        $priceStmt->execute(array_merge($symbols, [':start' => $start->format('Y-m-d'), ':end' => $end->format('Y-m-d')]));
        $prices = $priceStmt->fetchAll();

        // Pivot: date => symbol => close
        $priceByDate = [];
        foreach ($prices as $p) {
            $priceByDate[$p['price_date']][$p['symbol']] = (float) $p['close'];
        }

        // Build cash balance from transactions up to each date
        $cash = 0.0;
        $txByDate = [];
        foreach ($txs as $tx) {
            $ds = $tx->getDate()->format('Y-m-d');
            $txByDate[$ds][] = $tx;
        }

        $dates = array_keys($priceByDate);
        sort($dates);

        foreach ($dates as $ds) {
            // Apply today's transactions to cash BEFORE valuing
            foreach ($txByDate[$ds] ?? [] as $tx) {
                $amount = $tx->getAmount();
                // For buy: total is negative (cash out), for sell: total is positive (cash in)
                // Our transactions table already stores signed totals
                $cash += $amount;
            }

            // Value holdings at today's prices
            $holdingsValue = 0.0;
            foreach ($currentHoldings as $h) {
                $close = $priceByDate[$ds][$h['symbol']] ?? 0.0;
                $holdingsValue += $h['shares'] * $close;
            }

            // Total portfolio value = cash balance + holdings market value
            // NOTE: This approximates. Stockmarket doesn't have explicit cash accounts,
            // so cash is net of all transactions. Real accounting would track cash positions per account.
            $totalValue = $cash + $holdingsValue;
            if ($totalValue < 0) $totalValue = 0.0;

            $vals[] = new ValuationDTO(
                $portfolioId,
                new \DateTimeImmutable($ds),
                (float) $totalValue,
                'CAD'
            );
        }

        return $vals;
    }
}

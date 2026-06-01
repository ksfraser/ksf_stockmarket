<?php
/**
 * TransactionController — transaction history with filters.
 */
class TransactionController {

    /**
     * GET /?action=transactions — List transactions with optional filters.
     */
    public function listTransactions(
        string $account = '',
        string $symbol = '',
        string $type = '',
        string $dateFrom = '',
        string $dateTo = ''
    ): array {
        $pdo = Database::get();

        // Check if transactions table exists — if not, show message
        try {
            $pdo->query("SELECT 1 FROM transactions LIMIT 1");
        } catch (Exception $e) {
            return [
                'pageTitle' => 'Transactions',
                'template' => 'transactions',
                'transactions' => [],
                'accounts' => [],
                'symbols' => [],
                'note' => 'Transactions table not found. Import your transaction history to enable this feature.',
                'account_filter' => $account,
                'symbol_filter' => $symbol,
            ];
        }

        $where = [];
        $params = [];

        if ($account) {
            $where[] = "t.account_type = :acct";
            $params[':acct'] = $account;
        }
        if ($symbol) {
            $where[] = "t.symbol = :sym";
            $params[':sym'] = strtoupper($symbol);
        }
        if ($type) {
            $where[] = "t.type = :type";
            $params[':type'] = $type;
        }
        if ($dateFrom) {
            $where[] = "t.trade_date >= :dfrom";
            $params[':dfrom'] = $dateFrom;
        }
        if ($dateTo) {
            $where[] = "t.trade_date <= :dto";
            $params[':dto'] = $dateTo;
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        $sql = "SELECT t.*
                FROM transactions t
                {$whereSql}
                ORDER BY t.trade_date DESC, t.id DESC
                LIMIT 500";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        $transactions = $stmt->fetchAll();

        // Summary
        $summSql = "SELECT
                    COUNT(*) as total_count,
                    SUM(CASE WHEN t.type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN t.type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                    SUM(CASE WHEN t.type = 'DIVIDEND' THEN t.total ELSE 0 END) as total_dividends,
                    SUM(CASE WHEN t.type = 'BUY' THEN t.total ELSE 0 END) as total_buys,
                    SUM(CASE WHEN t.type = 'SELL' THEN t.total ELSE 0 END) as total_sells
                    FROM transactions t {$whereSql}";
        $stmt2 = $pdo->prepare($summSql);
        $stmt2->execute($params);
        $summary = $stmt2->fetch();

        // Filter options
        $accounts = array_column(
            $pdo->query("SELECT DISTINCT account_type FROM transactions ORDER BY account_type")->fetchAll(),
            'account_type'
        );
        $symbols = array_column(
            $pdo->query("SELECT DISTINCT symbol FROM transactions ORDER BY symbol")->fetchAll(),
            'symbol'
        );

        return [
            'pageTitle' => 'Transactions',
            'template' => 'transactions',
            'transactions' => $transactions,
            'summary' => $summary,
            'accounts' => $accounts,
            'symbols' => $symbols,
            'account_filter' => $account,
            'symbol_filter' => $symbol,
            'type_filter' => $type,
            'date_from' => $dateFrom,
            'date_to' => $dateTo,
        ];
    }
}

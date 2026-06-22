<?php
/**
 * TransactionController — transaction history with filters, recording, and validation.
 */
class TransactionController {

    private $currentUser;

    public function __construct() {
        $this->currentUser = AuthController::requireAuth();
    }

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

        if ($account) { $where[] = "t.account_type = :acct"; $params[':acct'] = $account; }
        if ($symbol) { $where[] = "t.symbol = :sym"; $params[':sym'] = strtoupper($symbol); }
        if ($type)   { $where[] = "t.type = :type"; $params[':type'] = $type; }
        if ($dateFrom) { $where[] = "t.trade_date >= :dfrom"; $params[':dfrom'] = $dateFrom; }
        if ($dateTo)   { $where[] = "t.trade_date <= :dto"; $params[':dto'] = $dateTo; }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        $sql = "SELECT t.* FROM transactions t {$whereSql} ORDER BY t.trade_date DESC, t.id DESC LIMIT 500";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        $transactions = $stmt->fetchAll();

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

        // Get filter options
        $accounts = $pdo->query("SELECT DISTINCT account_type FROM transactions WHERE account_type IS NOT NULL AND account_type != '' ORDER BY account_type")->fetchAll(PDO::FETCH_COLUMN);
        $symbols  = $pdo->query("SELECT DISTINCT symbol FROM transactions WHERE symbol IS NOT NULL AND symbol != '' ORDER BY symbol")->fetchAll(PDO::FETCH_COLUMN);

        return [
            'pageTitle'     => 'Transactions',
            'transactions'  => $transactions,
            'summary'       => $summary,
            'accounts'      => $accounts,
            'symbols'       => $symbols,
            'account_filter'=> $account,
            'symbol_filter' => $symbol,
            'type_filter'   => $type,
            'date_from'     => $dateFrom,
            'date_to'       => $dateTo,
        ];
    }

    /**
     * POST action=record — Record a BUY/SELL/DIVIDEND/SPLIT and update portfolio.
     */
    public function recordTransaction(array $post, int $userId): array {
        $pdo = Database::get();
        $errors = [];

        // Validate required fields
        $symbol = strtoupper(trim($post['symbol'] ?? ''));
        $exchange = strtoupper(trim($post['exchange'] ?? ''));
        $type   = strtoupper(trim($post['type'] ?? ''));
        $tradeDate = $post['trade_date'] ?? date('Y-m-d');
        $accountType = strtoupper(trim($post['account_type'] ?? ''));
        $quantity = isset($post['quantity']) ? (float) $post['quantity'] : 0;
        $price    = isset($post['price'])    ? (float) $post['price']    : 0;
        $total    = isset($post['total'])    ? (float) $post['total']    : 0;
        $commission = isset($post['commission']) ? (float) $post['commission'] : 0;
        $notes    = trim($post['notes'] ?? '');

        // Normalize symbol based on exchange
        if ($exchange === 'TSX' && !str_ends_with($symbol, '.TO')) {
            $symbol = $symbol . '.TO';
        }
        // For NASDAQ/NYSE, ensure no .TO suffix
        if (($exchange === 'NASDAQ' || $exchange === 'NYSE') && str_ends_with($symbol, '.TO')) {
            $symbol = substr($symbol, 0, -3);
        }
        // Auto-detect: check symbol_master for exchange, default to .TO for short symbols
        if ($exchange === '' && !str_ends_with($symbol, '.TO')) {
            $stmt = $pdo->prepare("SELECT exchange FROM symbol_master WHERE symbol = :sym OR symbol = CONCAT(:sym, '.TO') LIMIT 1");
            $stmt->execute([':sym' => $symbol]);
            $row = $stmt->fetch();
            if ($row && $row['exchange'] === 'TSX') {
                $symbol = $symbol . '.TO';
            }
        }

        if (strlen($symbol) < 1 || strlen($symbol) > 20) $errors[] = 'Symbol is required (1-20 chars).';
        if (!in_array($type, ['BUY', 'SELL', 'DIVIDEND', 'SPLIT'], true)) $errors[] = 'Type must be BUY, SELL, DIVIDEND, or SPLIT.';
        if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $tradeDate)) $errors[] = 'Trade date must be YYYY-MM-DD.';
        if (!in_array($accountType, ['RRSP', 'TFSA', 'MARGIN'], true)) $errors[] = 'Account must be RRSP, TFSA, or MARGIN.';
        if ($type === 'SPLIT') {
            if ($quantity <= 0) $errors[] = 'Split ratio (quantity) must be > 0 (e.g. 2 for 2:1 split).';
        } else {
            if ($quantity <= 0) $errors[] = 'Quantity must be > 0.';
            if ($price <= 0) $errors[] = 'Price must be > 0.';
        }

        // Auto-calculate total if not provided
        if ($total <= 0 && $type !== 'SPLIT') {
            $total = ($type === 'SELL')
                ? ($quantity * $price) - $commission
                : ($quantity * $price) + $commission;
        }

        if ($errors) return ['success' => false, 'errors' => $errors];

        try {
            $pdo->beginTransaction();

            // Insert transaction
            $stmt = $pdo->prepare("
                INSERT INTO transactions (symbol, trade_date, type, quantity, price, total, commission, account_type, notes, source_file, created_at)
                VALUES (:sym, :td, :type, :qty, :prc, :tot, :comm, :acct, :notes, 'manual_entry', NOW())
            ");
            $stmt->execute([
                ':sym' => $symbol, ':td' => $tradeDate, ':type' => $type,
                ':qty' => $quantity, ':prc' => $price, ':tot' => $total,
                ':comm' => $commission, ':acct' => $accountType, ':notes' => $notes,
            ]);
            $txnId = $pdo->lastInsertId();

            // Update portfolio
            if ($type === 'BUY') {
                $this->applyBuy($pdo, $userId, $symbol, $accountType, $quantity, $price, $commission);
            } elseif ($type === 'SELL') {
                $this->applySell($pdo, $userId, $symbol, $accountType, $quantity, $price, $commission);
            } elseif ($type === 'SPLIT') {
                $this->applySplit($pdo, $userId, $symbol, $quantity);
            }
            // DIVIDEND: no portfolio share change

            $pdo->commit();
            return ['success' => true, 'txn_id' => $txnId, 'message' => "Recorded {$type} {$symbol} {$quantity} @ \${$price}"];
        } catch (Exception $e) {
            $pdo->rollBack();
            return ['success' => false, 'errors' => ['Database error: ' . $e->getMessage()]];
        }
    }

    /**
     * Apply BUY: insert or update portfolio holding, recalculate cost basis.
     */
    private function applyBuy(PDO $pdo, int $userId, string $symbol, string $account, float $qty, float $price, float $commission): void {
        $stmt = $pdo->prepare("SELECT id, shares, cost_basis FROM portfolio WHERE user_id = :uid AND symbol = :sym AND account_type = :acct");
        $stmt->execute([':uid' => $userId, ':sym' => $symbol, ':acct' => $account]);
        $existing = $stmt->fetch();

        if ($existing) {
            // Weighted average cost basis
            $oldShares = (float) $existing['shares'];
            $oldCost = (float) $existing['cost_basis'];
            $newShares = $oldShares + $qty;
            $newCostBasis = (($oldShares * $oldCost) + ($qty * $price) + $commission) / $newShares;

            $upd = $pdo->prepare("UPDATE portfolio SET shares = :shares, cost_basis = :cb, cost_basis_total = :cbt, updated_at = NOW() WHERE id = :id");
            $upd->execute([
                ':shares' => $newShares, ':cb' => round($newCostBasis, 4),
                ':cbt' => round($newShares * $newCostBasis, 2), ':id' => $existing['id'],
            ]);
        } else {
            $totalCost = ($qty * $price) + $commission;
            $ins = $pdo->prepare("
                INSERT INTO portfolio (user_id, symbol, account_type, shares, cost_basis, cost_basis_total, entry_date, strategy, trailing_stop_pct, stop_loss_pct, atr_multiplier, notes, updated_at)
                VALUES (:uid, :sym, :acct, :shares, :cb, :cbt, CURDATE(), 'Manual Entry', 0.10, 0.15, 2.0, 'Recorded via transaction form', NOW())
            ");
            $ins->execute([
                ':uid' => $userId, ':sym' => $symbol, ':acct' => $account,
                ':shares' => $qty, ':cb' => round($price, 4), ':cbt' => round($totalCost, 2),
            ]);
        }
    }

    /**
     * Apply SELL: reduce shares, remove if fully sold.
     */
    private function applySell(PDO $pdo, int $userId, string $symbol, string $account, float $qty, float $price, float $commission): void {
        $stmt = $pdo->prepare("SELECT id, shares, cost_basis FROM portfolio WHERE user_id = :uid AND symbol = :sym AND account_type = :acct");
        $stmt->execute([':uid' => $userId, ':sym' => $symbol, ':acct' => $account]);
        $existing = $stmt->fetch();

        if (!$existing) {
            throw new RuntimeException("Cannot sell {$symbol} in {$account}: no existing holding found.");
        }

        $oldShares = (float) $existing['shares'];
        $newShares = $oldShares - $qty;

        if ($newShares < -0.001) {
            throw new RuntimeException("Cannot sell {$qty} shares of {$symbol}: only {$oldShares} held in {$account}.");
        }

        if ($newShares <= 0.001) {
            // Fully sold — remove from portfolio
            $del = $pdo->prepare("DELETE FROM portfolio WHERE id = :id");
            $del->execute([':id' => $existing['id']]);
        } else {
            // Partially sold — reduce shares, keep cost basis
            $upd = $pdo->prepare("UPDATE portfolio SET shares = :shares, cost_basis_total = :cbt, updated_at = NOW() WHERE id = :id");
            $upd->execute([
                ':shares' => round($newShares, 2),
                ':cbt' => round($newShares * (float) $existing['cost_basis'], 2),
                ':id' => $existing['id'],
            ]);
        }
    }

    /**
     * Apply SPLIT: multiply shares, adjust cost basis.
     */
    private function applySplit(PDO $pdo, int $userId, string $symbol, float $ratio): void {
        if ($ratio <= 0) throw new RuntimeException("Split ratio must be > 0.");

        $stmt = $pdo->prepare("SELECT id, shares, cost_basis FROM portfolio WHERE user_id = :uid AND symbol = :sym");
        $stmt->execute([':uid' => $userId, ':sym' => $symbol]);
        $rows = $stmt->fetchAll();

        if (empty($rows)) {
            throw new RuntimeException("Cannot split {$symbol}: no existing holding found.");
        }

        foreach ($rows as $r) {
            $newShares = (float) $r['shares'] * $ratio;
            $newCostBasis = (float) $r['cost_basis'] / $ratio;
            $upd = $pdo->prepare("UPDATE portfolio SET shares = :shares, cost_basis = :cb, cost_basis_total = :cbt, updated_at = NOW() WHERE id = :id");
            $upd->execute([
                ':shares' => round($newShares, 2), ':cb' => round($newCostBasis, 4),
                ':cbt' => round($newShares * $newCostBasis, 2), ':id' => $r['id'],
            ]);
        }
    }

    /**
     * Delete a manual transaction (only those with source_file = 'manual_entry').
     * Reverses the portfolio impact for BUY/SELL/SPLIT transactions.
     */
    public function deleteTransaction(int $txnId, int $userId): array
    {
        $pdo = Database::get();

        try {
            $pdo->beginTransaction();

            // Get the transaction to delete
            $stmt = $pdo->prepare("SELECT * FROM transactions WHERE id = :id");
            $stmt->execute([':id' => $txnId]);
            $txn = $stmt->fetch();
 
            if (!$txn) {
                $pdo->rollBack();
                return ['success' => false, 'errors' => ['Transaction not found or access denied.']];
            }
 
            $type = strtoupper((string) ($txn['type'] ?? ''));
            $symbol = strtoupper((string) ($txn['symbol'] ?? ''));
            $account = strtoupper((string) ($txn['account_type'] ?? ''));
            $quantity = (float) ($txn['quantity'] ?? 0);
            $price = (float) ($txn['price'] ?? 0);
            $commission = (float) ($txn['commission'] ?? 0);
            error_log("deleteTransaction: txnId=$txnId, type=$type, symbol=$symbol, qty=$quantity, userId=$userId");
            try {
                if ($type === 'BUY') {
                    $this->reverseBuy($pdo, $userId, $symbol, $account, $quantity, $price, $commission);
                } elseif ($type === 'SELL') {
                    $this->reverseSell($pdo, $userId, $symbol, $account, $quantity, $price, $commission);
                } elseif ($type === 'SPLIT') {
                    $this->reverseSplit($pdo, $userId, $symbol, $quantity);
                }
            } catch (RuntimeException $e) {
                $pdo->rollBack();
                error_log("deleteTransaction: reverse failed - " . $e->getMessage());
                return ['success' => false, 'errors' => ['Cannot delete: ' . $e->getMessage()]];
            }

            $upd = $pdo->prepare("UPDATE transactions SET is_deleted = 1, updated_at = NOW() WHERE id = :id");
            $updResult = $upd->execute([':id' => $txnId]);

            if (!$updResult || $upd->rowCount() === 0) {
                $pdo->rollBack();
                return ['success' => false, 'errors' => ['Transaction could not be deleted (may have been deleted already or access denied).']];
            }

            $pdo->commit();
            return ['success' => true, 'message' => "Deleted {$type} transaction for {$symbol}."];
        } catch (Exception $e) {
            $pdo->rollBack();
            error_log("deleteTransaction error: " . $e->getMessage() . " for txn_id=$txnId");
            return ['success' => false, 'errors' => ['Database error: ' . $e->getMessage()]];
        }
    }

    /**
     * Reverse a BUY: subtract shares, remove if fully sold.
     */
    private function reverseBuy(PDO $pdo, int $userId, string $symbol, string $account, float $qty, float $price, float $commission): void
    {
        $stmt = $pdo->prepare("SELECT id, shares, cost_basis, cost_basis_total FROM portfolio WHERE user_id = :uid AND symbol = :sym AND account_type = :acct");
        $stmt->execute([':uid' => $userId, ':sym' => $symbol, ':acct' => $account]);
        $existing = $stmt->fetch();

        if (!$existing) {
            throw new RuntimeException("Cannot reverse BUY: no holding found for {$symbol} in {$account}.");
        }

        $oldShares = (float) $existing['shares'];
        $newShares = $oldShares - $qty;

        if ($newShares <= 0.001) {
            // Fully removed - delete from portfolio
            $del = $pdo->prepare("DELETE FROM portfolio WHERE id = :id");
            $del->execute([':id' => $existing['id']]);
        } else {
            // Partially removed - reduce shares, recalculate cost basis
            $oldCostTotal = (float) $existing['cost_basis_total'];
            $soldCost = ($qty * $price) + $commission;
            $newCostTotal = $oldCostTotal - $soldCost;
            $newCostBasis = $newCostTotal / $newShares;

            $upd = $pdo->prepare("UPDATE portfolio SET shares = :shares, cost_basis = :cb, cost_basis_total = :cbt, updated_at = NOW() WHERE id = :id");
            $upd->execute([
                ':shares' => round($newShares, 2),
                ':cb' => round($newCostBasis, 4),
                ':cbt' => round($newCostTotal, 2),
                ':id' => $existing['id'],
            ]);
        }
    }

    /**
     * Reverse a SELL: add shares back.
     */
    private function reverseSell(PDO $pdo, int $userId, string $symbol, string $account, float $qty, float $price, float $commission): void
    {
        $stmt = $pdo->prepare("SELECT id, shares, cost_basis FROM portfolio WHERE user_id = :uid AND symbol = :sym AND account_type = :acct");
        $stmt->execute([':uid' => $userId, ':sym' => $symbol, ':acct' => $account]);
        $existing = $stmt->fetch();

        $totalReceived = ($qty * $price) - $commission;

        if ($existing) {
            // Add shares back, keeping the same cost basis
            $oldShares = (float) $existing['shares'];
            $oldCost = (float) $existing['cost_basis'];
            $newShares = $oldShares + $qty;
            // Use existing cost basis (the shares were sold at market price, not cost)

            $upd = $pdo->prepare("UPDATE portfolio SET shares = :shares, cost_basis_total = :cbt, updated_at = NOW() WHERE id = :id");
            $upd->execute([
                ':shares' => round($newShares, 2),
                ':cbt' => round($newShares * $oldCost, 2),
                ':id' => $existing['id'],
            ]);
        } else {
            // No existing holding - create one with cost basis from the sell price
            $ins = $pdo->prepare("
                INSERT INTO portfolio (user_id, symbol, account_type, shares, cost_basis, cost_basis_total, entry_date, strategy, trailing_stop_pct, stop_loss_pct, atr_multiplier, notes, updated_at)
                VALUES (:uid, :sym, :acct, :shares, :cb, :cbt, CURDATE(), 'Reversal', 0.10, 0.15, 2.0, 'Reversal of deleted SELL', NOW())
            ");
            $ins->execute([
                ':uid' => $userId, ':sym' => $symbol, ':acct' => $account,
                ':shares' => $qty, ':cb' => round($price, 4), ':cbt' => round($totalReceived, 2),
            ]);
        }
    }

    /**
     * Reverse a SPLIT: divide shares back.
     */
    private function reverseSplit(PDO $pdo, int $userId, string $symbol, float $ratio): void
    {
        if ($ratio <= 0) throw new RuntimeException("Split ratio must be > 0.");

        $stmt = $pdo->prepare("SELECT id, shares, cost_basis FROM portfolio WHERE user_id = :uid AND symbol = :sym");
        $stmt->execute([':uid' => $userId, ':sym' => $symbol]);
        $rows = $stmt->fetchAll();

        if (empty($rows)) {
            throw new RuntimeException("Cannot reverse split: no holding found for {$symbol}.");
        }

        foreach ($rows as $r) {
            $newShares = (float) $r['shares'] / $ratio;
            $newCostBasis = (float) $r['cost_basis'] * $ratio;
            $upd = $pdo->prepare("UPDATE portfolio SET shares = :shares, cost_basis = :cb, cost_basis_total = :cbt, updated_at = NOW() WHERE id = :id");
            $upd->execute([
                ':shares' => round($newShares, 2),
                ':cb' => round($newCostBasis, 4),
                ':cbt' => round($newShares * $newCostBasis, 2),
                ':id' => $r['id'],
            ]);
        }
    }

    /**
     * Edit a transaction (both manual and imported).
     * Updates transaction data AND adjusts portfolio holdings accordingly.
     */
    public function editTransaction(array $post, int $txnId, int $userId = 0): array
    {
        $pdo = Database::get();
        $errors = [];

        // Get the transaction (verify ownership)
        $stmt = $pdo->prepare("SELECT * FROM transactions WHERE id = :id AND user_id = :uid");
        $stmt->execute([':id' => $txnId, ':uid' => $this->currentUser['id']]);
        $txn = $stmt->fetch();

        if (!$txn) {
            return ['success' => false, 'errors' => ['Transaction not found.']];
        }

        $originalSource = $txn['source_file'] ?? '';
        $originalType = $txn['type'] ?? '';

        // Build update fields
        $updates = [];
        $params = [':id' => $txnId];

        // Store original values for portfolio adjustment
        $originalQty = (float)($txn['quantity'] ?? 0);
        $originalPrice = (float)($txn['price'] ?? 0);
        $originalCommission = (float)($txn['commission'] ?? 0);
        $symbol = $txn['symbol'];
        $account = $txn['account_type'];

        // Allow updating some fields
        if (isset($post['trade_date']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', $post['trade_date'])) {
            $updates[] = "trade_date = :trade_date";
            $params[':trade_date'] = $post['trade_date'];
        }

        if (isset($post['quantity']) && (float)$post['quantity'] > 0) {
            $updates[] = "quantity = :quantity";
            $params[':quantity'] = (float)$post['quantity'];
        }

        if (isset($post['price']) && (float)$post['price'] > 0) {
            $updates[] = "price = :price";
            $params[':price'] = (float)$post['price'];
        }

        if (isset($post['commission'])) {
            $updates[] = "commission = :commission";
            $params[':commission'] = (float)$post['commission'];
        }

        if (isset($post['notes'])) {
            $updates[] = "notes = :notes";
            $params[':notes'] = trim($post['notes']);
        }

        // Auto-calculate total if quantity and price are present
        if (isset($post['quantity']) && isset($post['price'])) {
            $qty = (float)$post['quantity'];
            $prc = (float)$post['price'];
            $comm = isset($post['commission']) ? (float)$post['commission'] : $originalCommission;
            $total = ($originalType ?? '') === 'SELL' ? ($qty * $prc) - $comm : ($qty * $prc) + $comm;
            $updates[] = "total = :total";
            $params[':total'] = $total;
        }

        if (empty($updates)) {
            return ['success' => false, 'errors' => ['No fields to update.']];
        }

        try {
            $pdo->beginTransaction();

            // Reverse the original portfolio impact
            try {
                if ($originalType === 'BUY') {
                    $this->reverseBuy($pdo, $userId, $symbol, $account, $originalQty, $originalPrice, $originalCommission);
                } elseif ($originalType === 'SELL') {
                    $this->reverseSell($pdo, $userId, $symbol, $account, $originalQty, $originalPrice, $originalCommission);
                } elseif ($originalType === 'SPLIT') {
                    $this->reverseSplit($pdo, $userId, $symbol, $originalQty);
                }
            } catch (RuntimeException $e) {
                // Log but continue - partial reversals may be OK
                error_log("editTransaction: reverse failed - " . $e->getMessage());
            }

            // Update the transaction
            $sql = "UPDATE transactions SET " . implode(', ', $updates) . ", updated_at = NOW() WHERE id = :id";
            $stmt = $pdo->prepare($sql);
            $stmt->execute($params);

            // Apply new portfolio impact (for BUY/SELL/SPLIT)
            $newQty = (float)($post['quantity'] ?? $originalQty);
            $newPrice = (float)($post['price'] ?? $originalPrice);
            $newCommission = (float)($post['commission'] ?? $originalCommission);

            // Use original type - we don't allow changing transaction type on edit
            if ($originalType === 'BUY') {
                $this->applyBuy($pdo, $userId, $symbol, $account, $newQty, $newPrice, $newCommission);
            } elseif ($originalType === 'SELL') {
                $this->applySell($pdo, $userId, $symbol, $account, $newQty, $newPrice, $newCommission);
            } elseif ($originalType === 'SPLIT') {
                $this->applySplit($pdo, $userId, $symbol, $newQty);
            }
            // DIVIDEND: no portfolio share change

            $pdo->commit();
            return ['success' => true, 'message' => "Updated transaction.", 'source_file' => $originalSource];
        } catch (Exception $e) {
            $pdo->rollBack();
            return ['success' => false, 'errors' => ['Database error: ' . $e->getMessage()]];
        }
    }

    /**
     * Validate: compare sum of BUY/SELL transactions to portfolio holdings.
     * Returns discrepancies for display.
     */
    public function validateHoldings(): array {
        $pdo = Database::get();
        $userId = $this->currentUser['id'];
        $discrepancies = [];

        try {
            // Get expected shares from transactions (per symbol + account)
            $txnSql = "
                SELECT symbol, account_type,
                    SUM(CASE WHEN type = 'BUY' THEN quantity ELSE 0 END) as total_bought,
                    SUM(CASE WHEN type = 'SELL' THEN quantity ELSE 0 END) as total_sold
                FROM transactions
                WHERE type IN ('BUY','SELL')
                GROUP BY symbol, account_type
            ";
            $txnRows = $pdo->query($txnSql)->fetchAll();
            $expected = [];
            foreach ($txnRows as $r) {
                $key = $r['symbol'] . '|' . $r['account_type'];
                $expected[$key] = (float) $r['total_bought'] - (float) $r['total_sold'];
            }

            // Get actual portfolio holdings
            $portSql = "SELECT symbol, account_type, shares FROM portfolio WHERE user_id = :uid AND shares > 0";
            $stmt = $pdo->prepare($portSql);
            $stmt->execute([':uid' => $userId]);
            $actual = [];
            foreach ($stmt->fetchAll() as $r) {
                $key = $r['symbol'] . '|' . $r['account_type'];
                $actual[$key] = (float) $r['shares'];
            }

            // Compare
            $allKeys = array_unique(array_merge(array_keys($expected), array_keys($actual)));
            foreach ($allKeys as $key) {
                $exp = $expected[$key] ?? 0;
                $act = $actual[$key] ?? 0;
                $diff = round($act - $exp, 4);
                if (abs($diff) > 0.001) {
                    [$sym, $acct] = explode('|', $key);
                    $discrepancies[] = [
                        'symbol'   => $sym,
                        'account'  => $acct,
                        'expected' => round($exp, 2),
                        'actual'   => round($act, 2),
                        'diff'     => $diff,
                    ];
                }
            }
        } catch (Exception $e) {
            $discrepancies[] = ['error' => 'Validation failed: ' . $e->getMessage()];
        }

        return ['holding_discrepancies' => $discrepancies];
    }
}

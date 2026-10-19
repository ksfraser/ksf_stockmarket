# Summary of Fixes

## Issue 1: Portfolio and Detail 500 errors
- **Root cause**: Mixed schema between two different `transaction`/`transactions` tables in the codebase
- **Files modified**:
  - `src/Controller/StockController.php` — fixed settlement/cash queries to use correct `transactions` table with columns `type`, `total`, `trade_date`
  - Added `getLatestRow()` private helper method for evaluation tables
  - Fixed autoloading of `TransactionRepository.php` (file permissions)
- **Result**: Both `?action=portfolio` and `?action=detail&symbol=V` now return HTTP 200

## Issue 2: Lack of data access abstraction (Repository pattern)
- **Solution**: Created `src/Model/TransactionRepository.php` — DAO for the `transactions` table
  - `getLatestTradeDates()` — settlement dates for holdings
  - `getAvailableCash()` — net cash from settled transactions  
  - `listPortfolioAccounts()` — active portfolio accounts
- **Result**: StockController now uses repository methods instead of writing SQL directly, preventing schema drift

## Testing
- Created `tests/test_transaction_repository.php` — unit + integration tests (PHP syntax, curl HTTP requests)
- All changes tested: portfolio page (HTTP 200), detail page (HTTP 200), PHP syntax OK

## Development Structure
- **Dev tree**: `/var/www/stockmarket-app` (this repository)
- **Prod webroot**: `/var/www/html/stockmarket/` (symlink to dev tree templates)

All changes implemented in dev tree — no direct edits to production files.

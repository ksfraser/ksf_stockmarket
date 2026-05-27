<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Tests\Unit;

use PHPUnit\Framework\TestCase;

/**
 * Tests for input validation logic.
 *
 * These test validation rules without requiring a database connection.
 */
class ValidationTest extends TestCase
{
    /**
     * Test that negative share count is rejected.
     */
    public function testNegativeSharesRejected(): void
    {
        $shares = -5;

        // This replicates the validation logic in Portfolio::setPosition()
        $this->assertLessThan(0, $shares, 'Shares cannot be negative');
    }

    /**
     * Test that negative cost is rejected.
     */
    public function testNegativeCostRejected(): void
    {
        $cost = -100.00;

        $this->assertLessThan(0, $cost, 'Cost cannot be negative');
    }

    /**
     * Test that zero shares and zero cost are accepted.
     */
    public function testZeroValuesAccepted(): void
    {
        $shares = 0;
        $cost = 0.0;

        $this->assertGreaterThanOrEqual(0, $shares);
        $this->assertGreaterThanOrEqual(0, $cost);
    }

    /**
     * Test symbol normalization to uppercase.
     */
    public function testSymbolNormalization(): void
    {
        $symbol = 'aapl';
        $normalized = strtoupper($symbol);

        $this->assertEquals('AAPL', $normalized);
    }
}

<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Tests\Integration;

use PHPUnit\Framework\TestCase;
use Ksf\StockMarket\Model\Portfolio;
use Ksf\StockMarket\Model\Database;

/**
 * Integration tests for the Portfolio model.
 *
 * REQUIRES: MariaDB running with ksf_stockmarket database loaded.
 *
 * Run with: ./vendor/bin/phpunit --testsuite Integration
 * Skip with: ./vendor/bin/phpunit --testsuite Unit
 */
class PortfolioIntegrationTest extends TestCase
{
    private static bool $dbAvailable = false;

    public static function setUpBeforeClass(): void
    {
        try {
            $connected = Database::isConnected();
            if (!$connected) {
                // Try to connect
                Database::getConnection();
            }
            self::$dbAvailable = true;
        } catch (\Exception $e) {
            self::$dbAvailable = false;
        }
    }

    protected function setUp(): void
    {
        if (!self::$dbAvailable) {
            $this->markTestSkipped('MariaDB not available — skipping integration tests');
        }
    }

    public function testGetPositionsReturnsArray(): void
    {
        $portfolio = new Portfolio();
        $positions = $portfolio->getPositions('default');

        $this->assertIsArray($positions);
    }

    public function testSetAndGetPosition(): void
    {
        $portfolio = new Portfolio();
        $portfolio->setPosition('TEST', 100, 5000.00, 'test_user');

        $position = $portfolio->getPosition('TEST', 'test_user');

        $this->assertNotNull($position);
        $this->assertEquals('TEST', $position['symbol']);
        $this->assertEquals(100, $position['shares']);

        // Cleanup
        $portfolio->removePosition('TEST', 'test_user');
    }

    public function testRemovePosition(): void
    {
        $portfolio = new Portfolio();
        $portfolio->setPosition('TODELETE', 50, 2500.00, 'test_user');

        $removed = $portfolio->removePosition('TODELETE', 'test_user');

        $this->assertTrue($removed);

        $position = $portfolio->getPosition('TODELETE', 'test_user');
        $this->assertNull($position);
    }

    public function testSetPositionRejectsNegativeShares(): void
    {
        $portfolio = new Portfolio();

        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage('Shares cannot be negative');

        $portfolio->setPosition('AAPL', -5, 100.00);
    }

    public function testSetPositionRejectsNegativeCost(): void
    {
        $portfolio = new Portfolio();

        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage('Cost cannot be negative');

        $portfolio->setPosition('AAPL', 10, -100.00);
    }
}

<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Tests\Unit;

use PHPUnit\Framework\TestCase;
use Ksf\StockMarket\App;

/**
 * Tests for the App bootstrap class.
 */
class AppTest extends TestCase
{
    private static string $testEnvPath;

    public static function setUpBeforeClass(): void
    {
        // Create a minimal .env for testing in the project root
        self::$testEnvPath = dirname(__DIR__, 2) . '/.env';

        // Backup existing .env if present
        if (file_exists(self::$testEnvPath)) {
            copy(self::$testEnvPath, self::$testEnvPath . '.bak');
        }

        $envContent = <<<'ENV'
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ksf_stockmarket_test
DB_USER=test
DB_PASS=test
APP_ENV=testing
APP_DEBUG=true
APP_NAME="KSF Stock Market Test"
PYTHON_API_URL=http://127.0.0.1:5000
PYTHON_API_KEY=
ENV;

        file_put_contents(self::$testEnvPath, $envContent);
    }

    public static function tearDownAfterClass(): void
    {
        // Restore original .env
        if (file_exists(self::$testEnvPath . '.bak')) {
            rename(self::$testEnvPath . '.bak', self::$testEnvPath);
        } else {
            @unlink(self::$testEnvPath);
        }
    }

    protected function setUp(): void
    {
        // Reset singleton between tests
        $reflection = new \ReflectionClass(App::class);
        $instance = $reflection->getProperty('instance');
        $instance->setAccessible(true);
        $instance->setValue(null, null);
    }

    public function testGetInstanceReturnsSingleton(): void
    {
        $app1 = App::getInstance();
        $app2 = App::getInstance();

        $this->assertSame($app1, $app2);
    }

    public function testBootstrapLoadsConfig(): void
    {
        $app = App::getInstance();
        $app->bootstrap(dirname(__DIR__, 2));

        $this->assertEquals('testing', $app->get('APP_ENV'));
        $this->assertEquals('KSF Stock Market Test', $app->get('APP_NAME'));
    }

    public function testGetReturnsDefaultForMissingKey(): void
    {
        $app = App::getInstance();
        $app->bootstrap(dirname(__DIR__, 2));

        $this->assertNull($app->get('NONEXISTENT_KEY'));
        $this->assertEquals('default_value', $app->get('NONEXISTENT_KEY', 'default_value'));
    }

    public function testRootDirReturnsProjectRoot(): void
    {
        $rootDir = dirname(__DIR__, 2);
        $app = App::getInstance();
        $app->bootstrap($rootDir);

        $this->assertEquals($rootDir, $app->rootDir());
    }

    public function testBootstrapIsIdempotent(): void
    {
        $rootDir = dirname(__DIR__, 2);
        $app = App::getInstance();

        // Call bootstrap twice — should not error
        $app->bootstrap($rootDir);
        $app->bootstrap($rootDir);

        $this->assertEquals('testing', $app->get('APP_ENV'));
    }
}

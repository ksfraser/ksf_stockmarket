<?php

declare(strict_types=1);

namespace Ksf\StockMarket;

use Dotenv\Dotenv;

/**
 * Application bootstrap and configuration.
 *
 * Loads environment variables, sets up autoloading,
 * and provides access to app configuration values.
 */
class App
{
    private static ?self $instance = null;

    /** @var array<string, mixed> */
    private array $config = [];

    /** @var bool */
    private bool $bootstrapped = false;

    private function __construct()
    {
    }

    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }

        return self::$instance;
    }

    /**
     * Bootstrap the application.
     *
     * Loads .env file, initializes autoloading, sets error handling.
     *
     * @param string $rootDir Project root directory
     */
    public function bootstrap(string $rootDir): void
    {
        if ($this->bootstrapped) {
            return;
        }

        // Load environment variables
        $dotenv = Dotenv::createImmutable($rootDir);
        $dotenv->safeLoad();

        // Store config
        $this->config = $_ENV;

        // Set error reporting based on environment
        if ($this->get('APP_DEBUG', false)) {
            error_reporting(E_ALL);
            ini_set('display_errors', '1');
        } else {
            error_reporting(E_ALL & ~E_DEPRECATED & ~E_STRICT);
            ini_set('display_errors', '0');
        }

        $this->bootstrapped = true;
    }

    /**
     * Get a configuration value.
     *
     * @param string $key     Config key
     * @param mixed  $default Default value if key not found
     * @return mixed
     */
    public function get(string $key, mixed $default = null): mixed
    {
        return $this->config[$key] ?? $default;
    }

    /**
     * Get the project root directory.
     */
    public function rootDir(): string
    {
        return dirname(__DIR__);
    }

    // Prevent cloning and unserialization
    private function __clone()
    {
    }

    public function __wakeup(): never
    {
        throw new \Exception('Cannot unserialize singleton');
    }
}

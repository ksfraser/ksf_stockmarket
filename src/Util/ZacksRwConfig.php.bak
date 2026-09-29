<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Util;

/**
 * Reads the `zacks_rw:` block from config.yaml (the canonical app config).
 *
 * Kept dependency-free: a tiny YAML reader that only understands top-level
 * map keys with indented scalar children, which is all the block needs.
 *
 * config.yaml:
 *   zacks_rw:
 *     inputs_dir: "/root/Inputs"        # where .und/.rpd corpus lives
 *     import_owner: "zacks_rw"          # system user owning imported screens
 *     max_rules_per_screen: 0           # 0 = no limit (screens store all rules)
 */
final class ZacksRwConfig
{
    /** @var array<string,mixed>|null */
    private static ?array $block = null;

    public static function inputsDir(): string
    {
        return (string) self::get('inputs_dir', getenv('RW_INPUTS_DIR') ?: '');
    }

    public static function importOwner(): string
    {
        return getenv('ZACKS_RW_OWNER') ?: (string) self::get('import_owner', 'zacks_rw');
    }

    public static function maxRulesPerScreen(): int
    {
        return (int) self::get('max_rules_per_screen', 0);
    }

    /** @return mixed */
    public static function get(string $key, mixed $default = null)
    {
        $block = self::block();
        return $block[$key] ?? $default;
    }

    /**
     * Resolve the config file: CLI override > cwd > repo-root candidates.
     *
     * @return string|null
     */
    public static function locate(): ?string
    {
        $candidates = [
            getenv('KSF_CONFIG') ?: null,
            './config.yaml',
            __DIR__ . '/../../config.yaml',
            '/var/www/stockmarket-app/config.yaml',
        ];
        foreach ($candidates as $c) {
            if ($c && is_file($c)) {
                return $c;
            }
        }
        return null;
    }

    /** @return array<string,mixed> */
    private static function block(): array
    {
        if (self::$block !== null) {
            return self::$block;
        }
        $path = self::locate();
        self::$block = $path ? self::readBlock($path) : [];
        return self::$block;
    }

    /** @return array<string,mixed> */
    private static function readBlock(string $path): array
    {
        $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if ($lines === false) {
            return [];
        }

        $inBlock = false;
        $blockIndent = 0;
        $parentIndent = -1;
        $parent = null;
        $result = [];

        foreach ($lines as $raw) {
            $raw = rtrim($raw);
            if ($raw === '' || str_starts_with(ltrim($raw), '#')) {
                continue;
            }
            $indent = self::indentOf($raw);
            if (!$inBlock) {
                if (preg_match('/^zacks_rw:\s*$/', ltrim($raw))) {
                    $inBlock = true;
                    $blockIndent = $indent;
                }
                continue;
            }
            // Inside the block: stop at a sibling with indent <= blockIndent.
            if ($indent <= $blockIndent) {
                $inBlock = false;
                continue;
            }
            $line = trim($raw);
            [$key, $value] = self::splitKeyValue($line);
            if ($key === null) {
                continue;
            }
            if ($value === null) {
                // Nested map header — remember parent for one more level.
                if ($parentIndent >= 0 && $indent > $parentIndent) {
                    $parent = $key;
                    $parentIndent = $indent;
                } elseif ($indent <= $parentIndent) {
                    $parent = null;
                    $parentIndent = -1;
                }
                continue;
            }
            if ($parent !== null && $indent > $parentIndent) {
                $result[$parent][$key] = $value;
            } elseif ($parent !== null) {
                $parent = null;
                $parentIndent = -1;
                $result[$key] = $value;
            } else {
                $result[$key] = $value;
            }
        }
        return $result;
    }

    private static function indentOf(string $raw): int
    {
        return strlen($raw) - strlen(ltrim($raw));
    }

    /** @return array{0:?string,1:mixed} */
    private static function splitKeyValue(string $line): array
    {
        if (!preg_match('/^([A-Za-z0-9_.-]+)\s*:(?:\s*(.*))?$/', $line, $m)) {
            return [null, null];
        }
        $key = $m[1];
        $value = $m[2] ?? '';
        if ($value === '') {
            return [trim($key), null];
        }
        return [trim($key), self::coerce(trim($value))];
    }

    private static function coerce(string $v): mixed
    {
        $v = trim($v);
        // Quoted value: honor the quote, whatever follows is a comment.
        if ($v !== '' && ($v[0] === '"' || $v[0] === "'")) {
            $q = $v[0];
            $close = strpos($v, $q, 1);
            if ($close !== false) {
                $v = substr($v, 1, $close - 1);
            }
        } elseif (str_contains($v, '#')) {
            // Unquoted scalar: anything after " #" is a comment.
            $v = trim(preg_replace('/\s+#.*$/', '', $v) ?? $v);
        }
        if (preg_match('/^-?\d+$/', $v)) {
            return (int) $v;
        }
        if (preg_match('/^-?\d+\.\d+$/', $v)) {
            return (float) $v;
        }
        if ($v === 'true') {
            return true;
        }
        if ($v === 'false') {
            return false;
        }
        return $v;
    }
}
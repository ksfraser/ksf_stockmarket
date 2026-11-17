<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Service;

use Ksf\ResearchWizard\Discovery\InputRepository;
use Ksf\ResearchWizard\Parser\UndParser;
use Ksf\ResearchWizard\Parser\ParserResult;
use Ksf\StockMarket\Util\ZacksRwConfig;
use PDO;

/**
 * Imports Research Wizard .und screen files into user_screens.
 *
 * Screens are stored for a dedicated system user (the "Zacks RW" importer
 * owner) with universe='stocks'. The stored filters_json is a faithful
 * serialization of every parsed rule atom (authoritative post-'!' tokens,
 * human operator text, timeframes, connective) so execution never needs the
 * original file again — and screens stay data-driven, not hand-entered.
 *
 * Re-running is an upsert keyed on (owner, name): existing screens are updated
 * in place, so import is idempotent and pick-up of new .und files is additive.
 */
final class ZacksScreenImporter
{
    private const ENGINE = 'zacks_rw';
    private const FIELDS_VERSION = 1;

    private UndParser $parser;
    private InputRepository $repository;

    public function __construct(private PDO $pdo)
    {
        $this->parser = new UndParser();
        $this->repository = new InputRepository();
    }

    /**
     * @return array{
     *     owner_id:int, owner:string, found:int, parsed_ok:int, inserted:int,
     *     updated:int, failed:int, parser_warnings:int, screens:array<int,array>
     * }
     */
    public function importAll(?string $dirOverride = null): array
    {
        $dir = $dirOverride ?: ZacksRwConfig::inputsDir();
        if ($dir === '') {
            throw new \RuntimeException('No RW inputs dir configured (config.yaml zacks_rw.inputs_dir).');
        }
        if (!is_dir($dir)) {
            throw new \RuntimeException("RW inputs dir not found: {$dir}");
        }

        $ownerName = ZacksRwConfig::importOwner();
        $ownerId = $this->ensureOwner($ownerName);

        $files = $this->repository->screens($dir);
        $result = [
            'owner_id' => $ownerId,
            'owner' => $ownerName,
            'found' => count($files),
            'parsed_ok' => 0,
            'inserted' => 0,
            'updated' => 0,
            'failed' => 0,
            'parser_warnings' => 0,
            'screens' => [],
        ];

        foreach ($files as $path) {
            $contents = @file_get_contents($path);
            if ($contents === false) {
                $result['failed']++;
                continue;
            }
            $parsed = $this->parser->parse($contents, basename($path), $path);
            if (count($parsed->screen->rules) === 0) {
                $result['failed']++;
                continue;
            }
            $result['parsed_ok']++;
            $result['parser_warnings'] += count($parsed->warnings);

            $screen = $parsed->screen;
            $name = $this->screenName($screen->name);
            $json = $this->buildFiltersJson($parsed);

            $existing = $this->pdo->prepare(
                "SELECT id FROM user_screens
                 WHERE user_id = ? AND universe = 'stocks' AND name = ? AND is_deleted = 0
                 LIMIT 1"
            );
            $existing->execute([$ownerId, $name]);
            $row = $existing->fetchColumn();

            $description = $this->describe($parsed->screen->rules);
            if ($row !== false) {
                $stmt = $this->pdo->prepare(
                    "UPDATE user_screens
                     SET filters_json = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                     WHERE id = ?"
                );
                $stmt->execute([$json, $description, (int) $row]);
                $result['updated']++;
            } else {
                $stmt = $this->pdo->prepare(
                    "INSERT INTO user_screens (user_id, name, description, universe, filters_json, is_public, is_deleted)
                     VALUES (?, ?, ?, 'stocks', ?, 0, 0)"
                );
                $stmt->execute([$ownerId, $name, $description, $json]);
                $result['inserted']++;
            }
            $result['screens'][] = ['name' => $name, 'rules' => count($parsed->screen->rules)];
        }

        return $result;
    }

    private function ensureOwner(string $username): int
    {
        $stmt = $this->pdo->prepare("SELECT id FROM users WHERE username = ? LIMIT 1");
        $stmt->execute([$username]);
        $id = $stmt->fetchColumn();
        if ($id !== false) {
            return (int) $id;
        }
        $hash = password_hash(bin2hex(random_bytes(16)), PASSWORD_DEFAULT);
        $ins = $this->pdo->prepare(
            "INSERT INTO users (username, email, password_hash, display_name, role, is_active)
             VALUES (?, ?, ?, 'Zacks RW Importer', 'user', 1)"
        );
        $ins->execute([$username, $username . '@local', $hash]);
        return (int) $this->pdo->lastInsertId();
    }

    private function screenName(string $basename): string
    {
        $name = trim(pathinfo($basename, PATHINFO_FILENAME));
        $name = preg_replace('/\s+/', ' ', $name) ?? $name;
        return mb_substr($name, 0, 118);
    }

    private function buildFiltersJson(ParserResult $parsed): string
    {
        $payload = [
            'engine' => self::ENGINE,
            'version' => self::FIELDS_VERSION,
            'source_file' => $parsed->screen->sourcePath,
            'report' => $parsed->screen->reportPath,
            'parsed_at' => date('Y-m-d H:i:s'),
            'rules' => array_map(
                static fn($atom) => $atom->toArray(),
                $parsed->screen->rules
            ),
        ];
        return json_encode($payload, JSON_UNESCAPED_SLASHES);
    }

    private function describe(array $rules): string
    {
        $n = count($rules);
        $custom = 0;
        foreach ($rules as $r) {
            if ($r->isCustomFormula()) {
                $custom++;
            }
        }
        $parts = ["{$n} rules"];
        if ($custom > 0) {
            $parts[] = "{$custom} custom formula";
        }
        return 'Imported from Research Wizard (.und): ' . implode(', ', $parts) . '.';
    }
}
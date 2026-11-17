<?php

declare(strict_types=1);

namespace ksfraser\StockMarket\Controller;

use ksfraser\StockMarket\Model\Database;



/**
 * ZacksScreenController — list and run imported Research Wizard stock screens.
 *
 * GET /?action=rw_screens         — list stock screens (data-driven from .und)
 * GET /?action=run_rw_screen&id=N — evaluate a stored screen on the live universe
 */
class ZacksScreenController {
    private $pdo;
    private $resolver;
    private $runner;

    public function __construct() {
        $this->pdo = Database::get();
        $this->resolver = new \ksfraser\StockMarket\Util\ZacksFieldResolver();
        $this->runner = new \ksfraser\StockMarket\Service\ZacksScreenRunner($this->resolver);
    }

    /**
     * List all stock-universe screens, most recently updated first.
     */
    public function listScreens(): array {
        $stmt = $this->pdo->query(
            "SELECT us.id, us.name, us.description, us.is_public, us.updated_at,
                    u.username AS owner, u.id AS owner_id
             FROM user_screens us
             JOIN users u ON u.id = us.user_id
             WHERE us.universe = 'stocks' AND us.is_deleted = 0
             ORDER BY us.updated_at DESC, us.name ASC"
        );
        return ['screens' => $stmt->fetchAll()];
    }

    /**
     * Run one stored screen against the live active universe.
     */
    public function runScreen(int $id): array {
        $stmt = $this->pdo->prepare(
            "SELECT us.*, u.username AS owner
             FROM user_screens us
             JOIN users u ON u.id = us.user_id
             WHERE us.id = ? AND us.universe = 'stocks' AND us.is_deleted = 0"
        );
        $stmt->execute([$id]);
        $screen = $stmt->fetch();
        if (!$screen) {
            return [
                'error' => "Screen #{$id} not found.",
                'screen' => null,
                'result' => null,
            ];
        }

        $payload = json_decode((string) $screen['filters_json'], true);
        if (!is_array($payload) || ($payload['engine'] ?? '') !== 'zacks_rw') {
            return [
                'error' => "Screen #{$id} is not a Zacks RW screen.",
                'screen' => $screen,
                'result' => null,
            ];
        }

        $rules = is_array($payload['rules'] ?? null) ? $payload['rules'] : [];

        $universe = new \ksfraser\StockMarket\Service\ZacksUniverse($this->pdo);
        $universe->setNeedVol20(\ksfraser\StockMarket\Service\ZacksScreenRunner::requiresVol20($rules, $this->resolver));
        $universe->load();

        $result = $this->runner->run($rules, $universe);
        $result['universe_size'] = $universe->count();
        $result['rule_count'] = count($rules);

        // Persist results into tradingview_screener_results for historical tracking
        $screenName = preg_replace('/[^a-z0-9_]/i', '_', (string)($screen['name'] ?? 'unknown'));
        $presetName = 'rw_screen_' . (int)$screen['id'] . '_' . $screenName;
        $market = 'america';

        // Remove previous results for this screen
        $this->pdo->prepare('DELETE FROM tradingview_screener_results WHERE preset_name = :pn')
            ->execute([':pn' => $presetName]);

        // Insert new results
        $insert = $this->pdo->prepare('
            INSERT INTO tradingview_screener_results (preset_name, market, symbol, data, run_at)
            VALUES (:pn, :mkt, :sym, :data, NOW())
        ');
        foreach ($result['symbols'] as $row) {
            $insert->execute([
                ':pn' => $presetName,
                ':mkt' => $market,
                ':sym' => $row['symbol'] ?? '',
                ':data' => json_encode($row, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            ]);
        }

        return [
            'error' => null,
            'screen' => $screen,
            'result' => $result,
            'source' => $payload['source_file'] ?? null,
            'persisted_count' => count($result['symbols']),
            'preset_name' => $presetName,
        ];
    }

    /**
     * GET /?action=create_rw_screen — show the screen builder form.
     * POST /?action=create_rw_screen — save a new screen to user_screens.
     */
    public function createScreen(): array
    {
        AuthController::requireAuth();
        $userId = (int)($_SESSION['user_id'] ?? 0);
        $pdo = Database::get();
        $resolver = new \ksfraser\StockMarket\Util\ZacksFieldResolver();

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $name = trim((string)($_POST['name'] ?? ''));
            $description = trim((string)($_POST['description'] ?? ''));
            $category = trim((string)($_POST['category'] ?? ''));
            $isPublic = isset($_POST['is_public']) ? 1 : 0;
            $isShared = isset($_POST['is_shared']) ? 1 : 0;
            $rulesRaw = $_POST['rules'] ?? [];

            // Normalize rules array
            $rules = [];
            if (is_array($rulesRaw)) {
                foreach ($rulesRaw as $r) {
                    $code = isset($r['code']) ? (int)$r['code'] : 0;
                    if ($code <= 0 || !$resolver->supports($code)) {
                        continue;
                    }
                    $operator = strtoupper(trim((string)($r['operator'] ?? 'EQ')));
                    $validOps = ['EQ','NE','GT','GE','LT','LE','IN','T#','B#','T%','B%'];
                    if (!in_array($operator, $validOps, true)) {
                        $operator = 'EQ';
                    }
                    $rules[] = [
                        'subject'    => (string)$code,
                        'code'       => $code,
                        'formula'    => null,
                        'timeframe'  => 'Recent',
                        'operator'   => $operator,
                        'raw_operator' => $operator,
                        'value'      => (string)($r['value'] ?? ''),
                        'connective' => in_array(strtoupper($r['connective'] ?? 'AND'), ['OR']) ? 'OR' : 'AND',
                        'raw'        => $code . '_Recent_' . $operator . '_' . (string)($r['value'] ?? '') . '_' . (in_array(strtoupper($r['connective'] ?? 'AND'), ['OR']) ? 'OR' : 'AND') . '_',
                        'name'       => $resolver->spec($code)['label'] ?? ('Field ' . $code),
                    ];
                }
            }

            if ($name === '' || empty($rules)) {
                return [
                    'pageTitle' => 'Create Screen',
                    'template'  => 'create_rw_screen',
                    'error'     => 'Screen name and at least one valid rule are required.',
                    'fields'    => $this->availableFields($resolver),
                    'operators' => $this->availableOperators(),
                ];
            }

            $payload = [
                'engine'      => 'zacks_rw',
                'version'     => 1,
                'source_file' => 'web_ui',
                'report'      => null,
                'parsed_at'   => date('Y-m-d H:i:s'),
                'rules'       => $rules,
            ];

            $stmt = $pdo->prepare('
                INSERT INTO user_screens (user_id, name, description, universe, filters_json, is_public, is_deleted, category, is_shared)
                VALUES (:uid, :name, :desc, :univ, :fj, :pub, 0, :cat, :shared)
            ');
            $stmt->execute([
                ':uid'  => $userId,
                ':name' => $name,
                ':desc' => $description,
                ':univ' => 'stocks',
                ':fj'   => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
                ':pub'  => $isPublic,
                ':cat'  => $category !== '' ? $category : null,
                ':shared' => $isShared,
            ]);

            header('Location: ?action=rw_screens');
            exit;
        }

        // GET — show form
        return [
            'pageTitle' => 'Create Screen',
            'template'  => 'create_rw_screen',
            'error'     => '',
            'fields'    => $this->availableFields($resolver),
            'operators' => $this->availableOperators(),
        ];
    }

    /** @return array<string, array<int, array{code:int,label:string}>> */
    private function availableFields(\ksfraser\StockMarket\Util\ZacksFieldResolver $resolver): array
    {
        $groups = [
            'Price & Momentum' => [],
            'Volume'           => [],
            'Fundamentals'     => [],
            'Other'            => [],
        ];
        foreach (\ksfraser\StockMarket\Util\ZacksFieldResolver::allSpecs() as $code => $spec) {
            $label = (string)($spec[0] ?? ('Field ' . $code));
            $source = (string)($spec[2] ?? '');
            $item = ['code' => $code, 'label' => $label];
            if ($source === 'price' || $source === 'win') {
                $groups['Price & Momentum'][] = $item;
            } elseif ($source === 'vol20' || $source === 'price') {
                $groups['Volume'][] = $item;
            } elseif ($source === 'fund') {
                $groups['Fundamentals'][] = $item;
            } else {
                $groups['Other'][] = $item;
            }
        }
        // Deduplicate Volume into Price & Momentum if needed
        if (empty($groups['Volume'])) {
            unset($groups['Volume']);
        }
        return $groups;
    }

    /** @return array<string, string> */
    private function availableOperators(): array
    {
        return [
            'EQ'  => '=',
            'NE'  => '≠',
            'GT'  => '>',
            'GE'  => '≥',
            'LT'  => '<',
            'LE'  => '≤',
            'IN'  => 'Between',
            'T#'  => 'Top #',
            'B#'  => 'Bottom #',
            'T%'  => 'Top %',
            'B%'  => 'Bottom %',
        ];
    }
}
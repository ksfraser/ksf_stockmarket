<?php
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
        $this->resolver = new \Ksf\StockMarket\Util\ZacksFieldResolver();
        $this->runner = new \Ksf\StockMarket\Service\ZacksScreenRunner($this->resolver);
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

        $universe = new \Ksf\StockMarket\Service\ZacksUniverse($this->pdo);
        $universe->setNeedVol20(\Ksf\StockMarket\Service\ZacksScreenRunner::requiresVol20($rules, $this->resolver));
        $universe->load();

        $result = $this->runner->run($rules, $universe);
        $result['universe_size'] = $universe->count();
        $result['rule_count'] = count($rules);

        return [
            'error' => null,
            'screen' => $screen,
            'result' => $result,
            'source' => $payload['source_file'] ?? null,
        ];
    }
}
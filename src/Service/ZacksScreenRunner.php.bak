<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Service;

use Ksf\ResearchWizard\Model\Operator;
use Ksf\StockMarket\Util\ZacksFieldResolver;

/**
 * Evaluates stored Zacks RW rule sets against the live universe.
 *
 * Semantics follow Research Wizard:
 *   - comparison operators apply per symbol; a symbol without data for a
 *     field is excluded from that rule (RW behaviour);
 *   - direct rank operators (T#/B#/T%/B%) select the top/bottom N (or %) of
 *     the active universe by the referenced metric;
 *   - group-rank variants rank within sectors (approximation);
 *   - unsupported atoms (custom formulas, aggregate references, unresolved
 *     field codes) are reported in `skipped` and treated as neutral so the
 *     remaining screen still executes honestly.
 *
 * Rules are joined AND, except chains linked by an OR connective which become
 * alternatives within one AND group (RW connectivity).
 */
final class ZacksScreenRunner
{
    public function __construct(private ZacksFieldResolver $resolver)
    {
    }

    public static function requiresVol20(array $rules, ZacksFieldResolver $resolver): bool
    {
        foreach ($rules as $r) {
            $code = isset($r['code']) ? (int) $r['code'] : null;
            if ($code === null) {
                continue;
            }
            $spec = $resolver->spec($code);
            if ($spec !== null && $spec['source'] === 'vol20') {
                return true;
            }
        }
        return false;
    }

    /**
     * @param array<int,array<string,mixed>> $rules  stored rule arrays
     * @return array{symbols:array<int,array>,skipped:array<int,array>,fully_executed:bool}
     */
    public function run(array $rules, ZacksUniverse $universe): array
    {
        $prepared = [];
        $skipped = [];
        foreach ($rules as $i => $r) {
            [$atom, $reason] = $this->prepare($i, $r);
            if ($atom === null) {
                $skipped[] = ['index' => $i, 'rule' => $r, 'reason' => $reason];
                continue;
            }
            $prepared[] = $atom;
        }

        // Pass mask per prepared atom.
        $pass = [];
        foreach ($prepared as $pi => $atom) {
            $pass[$pi] = $this->evaluate($atom, $universe);
        }

        // Combine connectives into OR-groups -> AND-groups.
        $groups = $this->groupRules($prepared);
        $groupIndices = [];
        $gi = 0;
        foreach ($groups as $g) {
            foreach ($g as $pi) {
                $groupIndices[$pi] = $gi;
            }
            $gi++;
        }

        $rows = [];
        foreach ($universe->rows() as $symbol => $row) {
            $ok = true;
            foreach ($groups as $group) {
                $groupOk = false;
                foreach ($group as $pi) {
                    if (($pass[$pi][$symbol] ?? false) === true) {
                        $groupOk = true;
                        break;
                    }
                }
                if (!$groupOk) {
                    $ok = false;
                    break;
                }
            }
            if (!$ok) {
                continue;
            }
            $rows[] = $this->renderRow($symbol, $row, $prepared, $pass);
        }

        usort($rows, fn($a, $b) => strcmp($a['symbol'], $b['symbol']));

        return [
            'symbols' => $rows,
            'skipped' => $skipped,
            'fully_executed' => count($skipped) === 0,
        ];
    }

    /**
     * @return array{0:?array,1:?string}
     */
    private function prepare(int $index, array $r): array
    {
        $code = isset($r['code']) && $r['code'] !== null ? (int) $r['code'] : null;
        if ($code === null) {
            if (!empty($r['formula'])) {
                return [null, 'custom formula: not executed'];
            }
            return [null, 'no subject code'];
        }
        $spec = $this->resolver->spec($code);
        if ($spec === null) {
            return [null, "field code {$code} has no data source in this app"];
        }

        $op = Operator::fromAtomToken((string) ($r['operator'] ?? $r['raw_operator'] ?? ''));
        if ($op === null) {
            return [null, 'unknown operator ' . ($r['operator'] ?? $r['raw_operator'] ?? '?')];
        }

        $value = (string) ($r['value'] ?? '');
        if ($value === '' && $op->isComparison()) {
            return [null, 'empty comparison value'];
        }

        if (($spec['type'] ?? 'numeric') === 'text' && !in_array($op, [Operator::EQ, Operator::NE], true)) {
            return [null, "operator {$op->value} not valid for text field"];
        }
        if ($op->isGroupRank() && !in_array($op, [Operator::TOP_N_SECTOR, Operator::TOP_N_MARKET_INDEX], true)) {
            return [null, "group-rank operator {$op->value} not supported (aggregate scoring)"];
        }

        $parsed = $this->parseValue($spec, $op, $value);
        if ($op->isRank() || in_array($op, [Operator::TOP_N_SECTOR, Operator::TOP_N_MARKET_INDEX], true)) {
            if (!is_numeric($value)) {
                return [null, "non-numeric rank value '{$value}' not supported"];
            }
        } elseif ($parsed === null) {
            return [null, "value '{$value}' not resolvable (aggregate/median reference?)"];
        }

        return [[
            'index' => $index,
            'spec' => $spec,
            'op' => $op,
            'textValue' => $value,
            'value' => $parsed,
            'parsedValue' => $value,
        ], null];
    }

    /** @return array|null numeric parsed value or null when not parseable */
    private function parseValue(array $spec, Operator $op, string $value): ?array
    {
        if ($op === Operator::IN_RANGE) {
            $parts = explode(':', $value, 2);
            if (count($parts) !== 2) {
                return null;
            }
            $lo = is_numeric(trim($parts[0])) ? (float) $parts[0] : null;
            $hi = is_numeric(trim($parts[1])) ? (float) $parts[1] : null;
            if ($lo === null || $hi === null) {
                return null;
            }
            return ['kind' => 'range', 'lo' => $lo, 'hi' => $hi];
        }
        if ($spec['type'] === 'text') {
            return ['kind' => 'text', 'value' => $value];
        }
        if (is_numeric($value)) {
            return ['kind' => 'num', 'value' => (float) $value];
        }
        // Aggregate references (Aggr(IM), XIndMed, ...) are not resolvable.
        return null;
    }

    /**
     * @return array<string,bool> symbol => pass
     */
    private function evaluate(array $atom, ZacksUniverse $universe): array
    {
        $op = $atom['op'];
        if ($op->isRank() || in_array($op, [Operator::TOP_N_SECTOR, Operator::TOP_N_MARKET_INDEX], true)) {
            return $this->evaluateRank($atom, $universe);
        }

        $out = [];
        foreach ($universe->rows() as $symbol => $row) {
            $metric = $this->metric($atom['spec'], $row);
            $out[$symbol] = $this->compare($metric, $op, $atom['value'], $atom['spec']);
        }
        return $out;
    }

    /** @return array<string,bool> */
    private function evaluateRank(array $atom, ZacksUniverse $universe): array
    {
        $op = $atom['op'];
        $limit = (int) $atom['parsedValue'];
        $isTop = in_array($op, [Operator::TOP_N, Operator::TOP_PCT, Operator::TOP_N_SECTOR, Operator::TOP_N_MARKET_INDEX], true);
        $isPct = in_array($op, [Operator::TOP_PCT, Operator::BOTTOM_PCT], true);
        $grouped = in_array($op, [Operator::TOP_N_SECTOR, Operator::TOP_N_MARKET_INDEX], true);

        // Collect metrics per symbol (optionally within group).
        $pool = [];
        foreach ($universe->rows() as $symbol => $row) {
            $metric = $this->metric($atom['spec'], $row);
            if ($metric === null) {
                continue;
            }
            $group = null;
            if ($grouped) {
                $group = $row['base']['sector'] ?? 'Unknown';
            }
            $pool[$group ?? '_'] [] = ['s' => $symbol, 'm' => (float) $metric];
        }

        $pass = [];
        foreach ($pool as $group => $items) {
            usort($items, fn($a, $b) => $isTop ? $b['m'] <=> $a['m'] : $a['m'] <=> $b['m']);
            $total = count($items);
            foreach ($items as $i => $it) {
                $order = $i + 1;
                $within = $isPct ? (($order / $total) * 100.0) <= $limit : $order <= $limit;
                $pass[$it['s']] = $within;
            }
        }
        // Symbols missing the metric fail the rank rule.
        foreach (array_keys($universe->rows()) as $symbol) {
            $pass[$symbol] = $pass[$symbol] ?? false;
        }
        return $pass;
    }

    /** @return mixed numeric|string|null */
    private function metric(array $spec, array $row)
    {
        $source = $spec['source'];
        $key = $spec['key'];
        $data = $row[$source] ?? null;
        if (is_array($data)) {
            $v = $data[$key] ?? null;
        } elseif ($source === 'vol20') {
            $v = $row['vol20'] ?? null;
        } else {
            $v = null;
        }
        return $v;
    }

    /** @param array|null $parsed parsed value, null when not parseable */
    private function compare(mixed $metric, Operator $op, ?array $parsed, array $spec): bool
    {
        if ($parsed === null) {
            return false;
        }
        // Missing data excludes the symbol (RW behaviour).
        if ($metric === null || $metric === '') {
            return false;
        }
        if ($spec['type'] === 'text' || $parsed['kind'] === 'text') {
            $a = strtolower(trim((string) $metric));
            $b = strtolower(trim((string) $parsed['value']));
            return $op === Operator::EQ ? $a === $b : $a !== $b;
        }
        $a = (float) $metric;
        switch ($op) {
            case Operator::IN_RANGE:
                return $a >= $parsed['lo'] && $a <= $parsed['hi'];
            case Operator::EQ:
                return abs($a - $parsed['value']) < 1e-9;
            case Operator::NE:
                return abs($a - $parsed['value']) >= 1e-9;
            case Operator::GT:
                return $a > $parsed['value'];
            case Operator::GE:
                return $a >= $parsed['value'];
            case Operator::LT:
                return $a < $parsed['value'];
            case Operator::LE:
                return $a <= $parsed['value'];
            default:
                return false;
        }
    }

    /** @return array<int,array<int,int>> groups of prepared-atom indices joined by OR within a group */
    private function groupRules(array $prepared): array
    {
        $groups = [];
        $current = [];
        $last = count($prepared) - 1;
        foreach ($prepared as $i => $atom) {
            $current[] = $i;
            $conn = strtoupper((string) ($atom['connective'] ?? 'AND'));
            if ($conn === 'OR' && $i < $last) {
                continue;
            }
            $groups[] = $current;
            $current = [];
        }
        return $groups;
    }

    /** @return array */
    private function renderRow(string $symbol, array $row, array $prepared, array $pass): array
    {
        $base = $row['base'] ?? [];
        $price = $row['price'] ?? [];
        $out = [
            'symbol' => $symbol,
            'name' => $base['name'] ?? '',
            'exchange' => $base['exchange'] ?? '',
            'close' => isset($price['close']) ? (float) $price['close'] : null,
            'price_date' => $price['price_date'] ?? null,
        ];
        $vals = [];
        foreach ($prepared as $pi => $atom) {
            $m = $this->metric($atom['spec'], $row);
            $vals[$atom['index']] = $m === null ? null : (is_float($m) ? round($m, 4) : $m);
        }
        $out['values'] = $vals;
        return $out;
    }
}
<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Util;

use Ksf\ResearchWizard\Contract\FieldBinding;
use Ksf\ResearchWizard\Contract\FieldResolverInterface;

/**
 * Binds Research Wizard field codes to live data sources in this app.
 *
 * Each code maps to a Spec:
 *   semantic   — stable machine name the evaluator keyed on
 *   type       — 'numeric' | 'text'
 *   source     — dataset the universe builder produces:
 *                  base   => symbol_master row
 *                  price  => latest stockprices row
 *                  fund   => latest fundamentals row
 *                  win    => computed price windows (stockprices)
 *                  vol20  => 20-day average volume (stockprices)
 *                  formula=> derived expression (see self::formula())
 *   key        — column / array key within that dataset
 *   approx     — true when the binding is an approximation of the RW semantic
 *
 * Codes absent from SPECS have no live data source yet; the importer still
 * stores them (full fidelity) and the runner surfaces them as skipped rules.
 */
final class ZacksFieldResolver implements FieldResolverInterface
{
    private const SPECS = [
        5   => ['price',                'numeric', 'price',   'close',             false],
        6   => ['daily_volume',         'numeric', 'price',   'volume',            false],
        8   => ['high_52w',             'numeric', 'win',     'high_52w',          false],
        9   => ['low_52w',              'numeric', 'win',     'low_52w',           false],
        10  => ['hl_range_pct',         'numeric', 'win',     'hl_range_pct',      false],
        11  => ['chg_4w',               'numeric', 'win',     'chg_4w',            false],
        13  => ['chg_12w',              'numeric', 'win',     'chg_12w',           false],
        15  => ['chg_24w',              'numeric', 'win',     'chg_24w',           false],
        17  => ['chg_ytd',              'numeric', 'win',     'chg_ytd',           false],
        19  => ['beta',                 'numeric', 'fund',    'beta',              false],
        20  => ['shares_outstanding',   'numeric', 'fund',    'shares_outstanding', false],
        21  => ['market_cap',           'numeric', 'fund',    'market_cap',        false],
        22  => ['avg_volume_20d',       'numeric', 'vol20',   'avg_volume_20d',    false],
        26  => ['dividend_yield',       'numeric', 'fund',    'dividend_yield',    false],
        34  => ['eps_12m',              'numeric', 'fund',    'trailing_eps',      true],
        35  => ['eps_growth_5yr',       'numeric', 'fund',    'zacks_eps_growth_5yr', false],
        44  => ['eps_revision_q1_4w',   'numeric', 'fund',    'zacks_eps_change_f1_4w', true],
        49  => ['f1_eps_estimate',      'numeric', 'fund',    'forward_eps',       true],
        54  => ['eps_revision_f1_4w',   'numeric', 'fund',    'zacks_eps_change_f1_4w', false],
        55  => ['eps_revision_f1_12w',  'numeric', 'fund',    'zacks_eps_change_f1_12w', false],
        64  => ['eps_revision_f2_12w',  'numeric', 'fund',    'zacks_eps_change_f1_12w', true],
        68  => ['eps_growth_lt',        'numeric', 'fund',    'zacks_eps_growth_lt_3_5yr', false],
        71  => ['num_analysts',         'numeric', 'fund',    'zacks_num_analysts', false],
        72  => ['pe_f1',                'numeric', 'fund',    'forward_pe',        true],
        74  => ['pe_f2',                'numeric', 'fund',    'forward_pe',        true],
        76  => ['pe_12m',               'numeric', 'fund',    'trailing_pe',       false],
        93  => ['roe',                  'numeric', 'fund',    'roe',               false],
        95  => ['roa',                  'numeric', 'fund',    'roa',               false],
        100 => ['price_to_book',        'numeric', 'fund',    'price_to_book',     false],
        105 => ['cash_flow',            'numeric', 'fund',    'operating_cash_flow', false],
        106 => ['cash_flow_share',      'numeric', 'fund',    'fcf_per_share',     true],
        107 => ['price_cash_flow',      'numeric', 'fund',    'price_to_sales',    true],
        120 => ['chg_1w',               'numeric', 'win',     'chg_1w',            false],
        122 => ['chg_52w',              'numeric', 'win',     'chg_52w',           false],
        155 => ['sales_12m',            'numeric', 'fund',    'total_revenue',     false],
        171 => ['roi',                  'numeric', 'fund',    'zacks_roi',         false],
        173 => ['net_margin',           'numeric', 'fund',    'profit_margin',     false],
        175 => ['op_margin',            'numeric', 'fund',    'operating_margin',  false],
        181 => ['asset_turnover',       'numeric', 'fund',    'zacks_asset_turnover_ttm', false],
        185 => ['debt_capital_pct',     'numeric', 'fund',    'zacks_lt_debt_capital_pct', false],
        192 => ['zacks_rank',           'numeric', 'fund',    'zacks_rank',        false],
        505 => ['exchange',             'text',    'base',    'exchange',          false],
        507 => ['chg_vs_high_52w',      'numeric', 'win',     'chg_vs_high_52w',   false],
        525 => ['eps_growth_q0_q4',     'numeric', 'fund',    'zacks_eps_growth_q0_q4', false],
        529 => ['eps_growth_f1_f0',     'numeric', 'fund',    'zacks_eps_pct_change_f1_f0', false],
        532 => ['price_to_sales',       'numeric', 'fund',    'price_to_sales',    false],
        551 => ['peg_ratio',            'numeric', 'fund',    'peg_ratio',         false],
        554 => ['debt_to_equity',       'numeric', 'fund',    'debt_to_equity',    false],
        575 => ['sales_growth_12m',     'numeric', 'fund',    'revenue_growth',    true],
        577 => ['sales_growth_q0_q4',   'numeric', 'fund',    'zacks_sales_growth_reported_q', false],
        645 => ['fwd_actual_pe',        'numeric', 'fund',    'forward_pe',        true],
        646 => ['pe_fwd_12m',           'numeric', 'fund',    'forward_pe',        true],
    ];

    public function resolve(int $code): ?FieldBinding
    {
        $spec = $this->spec($code);
        if ($spec === null) {
            return null;
        }
        return new FieldBinding(
            $code,
            $spec['semantic'],
            null,
            $this->higherIsBetter($code),
        );
    }

    public function spec(int $code): ?array
    {
        $row = self::SPECS[$code] ?? null;
        if ($row === null) {
            return null;
        }
        return [
            'code'      => $code,
            'semantic'  => $row[0],
            'type'      => $row[1],
            'source'    => $row[2],
            'key'       => $row[3],
            'approx'    => $row[4],
            'label'     => (string) ($row[0] ?? ''),
        ];
    }

    public function supports(int $code): bool
    {
        return isset(self::SPECS[$code]);
    }

    private function higherIsBetter(int $code): bool
    {
        return in_array($code, [68, 71, 93, 95, 171, 173, 175, 192], true);
    }
}
<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Tests\Unit;

use Ksf\StockMarket\Util\StockFilter;
use PHPUnit\Framework\TestCase;

/**
 * Unit tests for the All Symbols filter engine (StockFilter).
 *
 * Covers the WHERE-builder contract used by the Zacks filter architecture:
 * multi-tag OR groups are parenthesized, bare-number tags become equality,
 * Zacks grade filters are exact-match text IN, market-cap shorthand is parsed
 * (including '1B+'), and fcf_yield (a non-existent column) is never emitted.
 */
final class StockFilterTest extends TestCase
{
    private static function makeFilter(): StockFilter
    {
        $ref = new \ReflectionClass(StockFilter::class);
        /** @var StockFilter $sf */
        return $ref->newInstanceWithoutConstructor();
    }

    public function testMarketCapShorthandParsing(): void
    {
        $this->assertSame([1_000_000_000.0, null], array_values(StockFilter::parseMarketCapRange('1B+') ?? []));
        $this->assertSame([null, 500_000_000.0], array_values(StockFilter::parseMarketCapRange('500M-') ?? []));
        $this->assertSame([100_000_000.0, 500_000_000.0], array_values(StockFilter::parseMarketCapRange('100M-500M') ?? []));
        $this->assertSame([500_000.0, null], array_values(StockFilter::parseMarketCapRange('500K+') ?? []));
        $this->assertNull(StockFilter::parseMarketCapRange('all'));
    }

    public function testMultiTagRankEqualityIsParenthesizedWithDistinctParams(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere(['zacks_rank' => ['1', '2']]);
        $this->assertStringContainsString(
            '(ABS(f.zacks_rank - :sf_zrank_eq0) < 0.0001 OR ABS(f.zacks_rank - :sf_zrank_eq1) < 0.0001)',
            $r['where'],
        );
        $this->assertSame(1.0, $r['params'][':sf_zrank_eq0']);
        $this->assertSame(2.0, $r['params'][':sf_zrank_eq1']);
    }

    public function testVgmGradeFilterBecomesTextInClause(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere(['zacks_vgm_grade' => ['a', 'B']]);
        $this->assertStringContainsString('f.zacks_vgm_grade IN (:sf_zacks_vgm_grade_v0,:sf_zacks_vgm_grade_v1)', $r['where']);
        $this->assertSame('A', $r['params'][':sf_zacks_vgm_grade_v0']);
        $this->assertSame('B', $r['params'][':sf_zacks_vgm_grade_v1']);
    }

    public function testMarketCapMultiTagParenthesizedOr(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere(['market_cap' => ['1B+', '500M-']]);
        $this->assertStringContainsString(
            '(f.market_cap >= :sf_mcap_lo OR f.market_cap <= :sf_mcap_hi)',
            $r['where'],
        );
    }

    public function testFcfYieldIsNeverReferenced(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere(['fcf_yield' => ['0-5']]);
        $this->assertStringNotContainsString('fcf_yield', $r['where']);
    }

    public function testZacksRevisionColumnIsFilterable(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere(['zacks_eps_change_f1_4w' => ['0+']]);
        $this->assertStringContainsString('f.zacks_eps_change_f1_4w >= :sf_zacks_eps_change_f1_4w_lo', $r['where']);
    }

    public function testPriceChangeWindowReference(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere(['perf_4q' => ['5-20']]);
        $this->assertStringContainsString('perf_4q >= :sf_perf_4q_lo AND perf_4q <= :sf_perf_4q_hi', $r['where']);
    }

    public function testCombineOrKeepsBaseColumns(): void
    {
        $sf = self::makeFilter();
        $r = $sf->buildWhere([
            'zacks_vgm_grade' => ['A'],
            'zacks_rank'      => ['2'],
            'combine'         => 'or',
        ]);
        $this->assertStringContainsString('sm.is_active = 1', $r['where']);
        $this->assertStringContainsString('latest.max_date IS NOT NULL', $r['where']);
        $this->assertStringContainsString('OR', $r['where']);
    }
}
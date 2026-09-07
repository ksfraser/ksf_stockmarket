<?php

declare(strict_types=1);

namespace Ksf\StockMarket\Tests\Unit;

use Ksf\ResearchWizard\Contract\FieldBinding;
use Ksf\StockMarket\Util\ZacksFieldResolver;
use PHPUnit\Framework\TestCase;

/**
 * Unit tests for the Research Wizard field-code binding layer.
 */
final class ZacksFieldResolverTest extends TestCase
{
    private ZacksFieldResolver $resolver;

    protected function setUp(): void
    {
        $this->resolver = new ZacksFieldResolver();
    }

    public function testCorpusCommonCodesResolveToLiveSources(): void
    {
        // The five most frequent field codes in the 215-screen corpus.
        $expect = [
            5   => ['price',            'price'],
            11  => ['chg_4w',           'win'],
            21  => ['market_cap',       'fund'],
            22  => ['avg_volume_20d',   'vol20'],
            192 => ['zacks_rank',       'fund'],
        ];
        foreach ($expect as $code => [$semantic, $source]) {
            $spec = $this->resolver->spec($code);
            $this->assertNotNull($spec, "spec for code {$code}");
            $this->assertSame($semantic, $spec['semantic']);
            $this->assertSame($source, $spec['source']);
            $this->assertSame('numeric', $spec['type']);
            $this->assertTrue($this->resolver->supports($code));
        }
    }

    public function testTextFieldResolvesAsText(): void
    {
        $spec = $this->resolver->spec(505);
        $this->assertNotNull($spec);
        $this->assertSame('exchange', $spec['semantic']);
        $this->assertSame('text', $spec['type']);
        $this->assertSame('base', $spec['source']);
    }

    public function testUnknownCodeResolvesNull(): void
    {
        $this->assertNull($this->resolver->spec(621));
        $this->assertNull($this->resolver->resolve(621));
        $this->assertFalse($this->resolver->supports(621));
    }

    public function testResolveReturnsFieldBinding(): void
    {
        $binding = $this->resolver->resolve(192);
        $this->assertInstanceOf(FieldBinding::class, $binding);
        $this->assertSame(192, $binding->code);
        $this->assertSame('zacks_rank', $binding->semantic);
        $this->assertTrue($binding->higherIsBetter);
    }
}
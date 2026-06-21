<?php

use PHPUnit\Framework\TestCase;

require_once '/home/ksf_stockmarket/ksf_stockmarket/php/src/Controller/StockController.php';

final class StockControllerTest extends TestCase
{
    public function test_controller_class_exists_and_is_loadable(): void
    {
        $this->assertTrue(class_exists('StockController', false));
    }

    public function test_controller_has_new_methods_and_properties(): void
    {
        $rc = new ReflectionClass('StockController');
        $this->assertTrue($rc->hasMethod('detail'));
        $this->assertTrue($rc->hasMethod('getLatestIndicators'));
        $this->assertTrue($rc->hasMethod('getTableData'));
    }
}

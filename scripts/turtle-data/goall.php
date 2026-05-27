<?php

//process all stocks

require_once( '../../model/include_all.php' );
require_once( '../../model/stockprices.class.php' );
require_once( '../../model/turtledata.class.php' );
require_once( 'calcturtle.php' );

$turtledata = new turtledata();
$turtledata->select = "distinct symbol, max(date) as date";
//$turtledata->where = "symbol not in (select distinct symbol from turtledata) group by symbol";
$turtledata->groupby = "symbol";
$turtledata->nolimit = TRUE;
$turtledata->Select();
foreach( $turtledata->resultarray as $row )
{
	echo "goall Calc " . $row['symbol'] . " starting on " . $row['date'] . "\n";
	//Calculate for existing, from the last time this was run
	calcturtle( $row['symbol'], $row['date'] );
//	calcturtle( $row['symbol'] ); //Defaults to 2008-01-01
}

//exit();

$stockprices = new stockprices();
$stockprices->select = "distinct symbol, min(date) as date";
$stockprices->where = "symbol not in (select distinct symbol from turtledata) group by symbol";
$stockprices->nolimit = TRUE;
$stockprices->Select();
foreach( $stockprices->resultarray as $row )
{
	echo "Calc " . $row['symbol'] . " starting on " . $row['date'] . "\n";
	calcturtle( $row['symbol'], $row['date'] );
//	calcturtle( $row['symbol'] ); //defualts to 2008-01-01
}

?>

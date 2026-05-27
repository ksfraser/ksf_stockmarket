<?php

//20090718 KF Generate candlesticks for ALL stocks

require_once( '../model/include_all.php' );
require_once( '../model/stockprices.class.php' );
require_once( 'candlesticks.report.php' );
require_once( 'heikanashi.report.php' );

$stockinfo = new stockprices();
$stockinfo->select = "distinct symbol";
$stockinfo->nolimit = TRUE;
$stockinfo->Select();

foreach( $stockinfo->resultarray as $row )
{
	//Check for existance of directory to put reports into
	$dir = REPORTDIR . "/" . $row['symbol'];
	if (!is_dir( $dir ) ) mkdir( $dir, 0775 );
	candlesticks_report( 31, $row['symbol'] );	
	heikanashi_report( 31, $row['symbol'] );	
}

?>

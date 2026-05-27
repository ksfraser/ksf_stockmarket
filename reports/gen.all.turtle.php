#!/usr/bin/php
<?php

//20090718 KF Generate candlesticks for ALL stocks

require_once( '../model/include_all.php' );
require_once( '../model/stockprices.class.php' );
require_once( 'turtledata.report.php' );

$stockinfo = new stockprices();
$stockinfo->select = "distinct symbol";
//20100824 KF 212 Fix report
$stockinfo->nolimit = TRUE;
//20100824 !212
$stockinfo->Select();

foreach( $stockinfo->resultarray as $row )
{
	//Check for existance of directory to put reports into
	$dir = REPORTDIR . "/" . $row['symbol'];
	if (!is_dir( $dir ) ) mkdir( $dir, 0775 );
	report_default( 77, $row['symbol'] );	
}

?>

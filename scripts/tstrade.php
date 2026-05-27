<?php

/*20090701 KF
* 	File to take the stockprices data
*	and output it in the time series
*	database format as expected by
*	the tsinvest program
*
*	format is:
*	Date \t	Symbol \t Price
*
*	One symbol per row
*	Symbols in date order from
*	oldest to newest
*/

require_once( 'include_all.php' );
require_once( '/var/www/html/finance/model/stockprices.class.php' );

$stockprice = new stockprices();
$stockprice->orderby = "date asc";
$stockprice->Select();

$fp = fopen( "stocks.tstrade.txt", "w" );
if ($fp != NULL )
{
	foreach( $stockprice->resultarray as $row )
	{	
		fwrite( $fp, fprintf( "%s\t%s\t%s\t%s\t%s\t%s\n", $row['date'], $row['symbol'], $row['day_high'], $row['day_low'], $row['day_close'], $row['volume'] ) );
	}
}
fclose( $fp );
	

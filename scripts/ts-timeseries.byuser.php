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
*
*	Do this on a user by user
*	basis so that their portfolio
*	can also be backtested
*/
echo __FILE__;

require_once( 'include_all.php' );
require_once( $MODELDIR . '/users.class.php' );
$users = new users();
$users->Select();
foreach( $users->resultarray as $row )
{
	$thisuser = $row['username'];
	//Get list of stocks the user owns
	require_once( $MODELDIR . '/portfolio.class.php' );
	$portfolio = new portfolio();
	$portfolio->where = "username = '$thisuser' and numbershares > 0 and stocksymbol not in ( 'CASH', 'BOO' )";
	$portfolio->fieldspec['username']['extra_sql'] = "";
	$portfolio->Select();
//	var_dump( $portfolio->querystring );
//	var_dump( $portfolio->resultarray );
	$symbollist = "";
	$count = 0;
	foreach( $portfolio->resultarray as $row )
	{
		if( $count > 0 )
			$symbollist .= ", ";
		$symbollist .= "'" . $row['stocksymbol'] . "'";
		$count++;
	}
	var_dump( $symbollist );
	
	if( strlen( $symbollist ) > 2 )
	{
		require_once( $MODELDIR . '/stockprices.class.php' );
		$stockprice = new stockprices();
		$stockprice->orderby = "date asc";
		$stockprice->where = "symbol in ( $symbollist ) ";
		$stockprice->Select();
//		echo "\n";
//		var_dump( $stockprice->querystring );
//		echo "\n";

		$fp = fopen( "../currentdata/stocks.timeseries." . $thisuser . ".txt", "w" );
		if ($fp != NULL )
		{
			foreach( $stockprice->resultarray as $row )
			{	
				fwrite( $fp, sprintf( "%s\t%s\t%s\n", $row['date'], $row['symbol'], $row['day_close'] ) );
			}
		}
		fclose( $fp );
	}
}
	

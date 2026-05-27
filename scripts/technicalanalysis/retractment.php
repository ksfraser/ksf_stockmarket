<?php

//20090806 KF
//Retractment is where the price has dropped from the high in a defined time period.
/*20130904 KF Eventum 243 removed "as high" after symbol in query */

//select * from stockprices where symbol = 'IBM' and date in ( (select date from stockprices where symbol = 'IBM' and date > DATE_SUB(CURDATE(), INTERVAL 14 DAY) order by day_close desc limit 1),  (select date from stockprices where symbol = 'IBM' and date > DATE_SUB(CURDATE(), INTERVAL 3 DAY) order by date desc limit 1));

//Eventum #146
function isretractment( $symbol, $days, $volatilitypercent = 1 )
{
        if( percentretractment( $symbol, $days ) > $volatilitypercent )
                return 1;
        else
                return 0;
}
//!146

function percentretractment( $symbol, $days )
{
//How much retractment for a symbol in days 
//RETURNS -101, -102, -103 on ERROR

	require_once( MODELDIR . '/include_all.php' );
	require_once( MODELDIR . '/stockprices.class.php' );
	$stockprices = new stockprices;

	//$maxhigh = "select max(day_close) as high from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
	//$maxhigh = "select max(day_high) as high from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
/*20130904 KF Eventum 243 removed "as high" after symbol in query */
	$maxhigh = "select day_high as high,date,symbol from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY ) order by high desc limit 1";
	$stockprices->querystring = $maxhigh;
	$stockprices->GenericQuery();
	if( isset( $stockprices->resultarray[0]['high'] ))
		$high = $stockprices->resultarray[0]['high'];
	else
	{
		unset( $stockprices );
		return "-101";
	}

	$stockprices->querystring = "select * from stockprices where symbol = '" . $symbol . "' order by date desc limit 1";
	$stockprices->GenericQuery();

	if( isset( $stockprices->resultarray[0]['day_close'] ))
	{
		$today = $stockprices->resultarray[0]['day_close'];
		//var_dump( $stockprices->resultarray[0] );
		//var_dump( $high );
	}
	else
	{
		unset( $stockprices );
		return "-102";
	}
	
	if( $high <> 0)
		$percentretractment = (1 - $today/$high) * 100;
	else
		$percentretractment = "-103";
	unset( $stockprices );
	return $percentretractment;
}

function dollarretractment( $symbol, $days )
{
//How much retractment for a symbol in days 

	require_once( MODELDIR . '/include_all.php' );
	require_once( MODELDIR . '/stockprices.class.php' );
	$stockprices = new stockprices;
	
	//$maxhigh = "select max(day_close) as high from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
	$maxhigh = "select max(day_high) as high from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
	$stockprices->querystring = $maxhigh;
	$stockprices->GenericQuery();
	if( isset( $stockprices->resultarray[0]['high'] ))
		$high = $stockprices->resultarray[0]['high'];
	else
	{
		unset( $stockprices );
		return "-101";
	}

	$stockprices->querystring = "select * from stockprices where symbol = '" . $symbol . "' order by date desc limit 1";
	$stockprices->GenericQuery();

	if( isset( $stockprices->resultarray[0]['day_close'] ))
	{
		$today = $stockprices->resultarray[0]['day_close'];
		//var_dump( $stockprices->resultarray[0] );
		//var_dump( $high );
	}
	else
	{
		unset( $stockprices );
		return "-102";
	}

	$dollarretractment = $high - $today;
	return $dollarretractment;
}


//test
/*
define( 'MODELDIR', '/mnt/2/development/var/www/html/finance/model/' );
echo "Retractment of IBM is " . dollarretractment( "IBM", "14" ) . " for a percentage of " . percentretractment( "IBM", "14" );
echo "Retractment of MX is " . dollarretractment( "MX", "14" ) . " for a percentage of " . percentretractment( "MX", "14" );
echo "Retractment of MEOH is " . dollarretractment( "MEOH", "14" ) . " for a percentage of " . percentretractment( "MEOH", "14" );
echo "Retractment of SLV is " . dollarretractment( "SLV", "14" ) . " for a percentage of " . percentretractment( "SLV", "14" );
*/
?>

<?php

//20090806 KF
//Advancement is where the price has increased from the low in a defined time period.

//select * from stockprices where symbol = 'IBM' and date in ( (select date from stockprices where symbol = 'IBM' and date > DATE_SUB(CURDATE(), INTERVAL 14 DAY) order by day_close asc limit 1),  (select date from stockprices where symbol = 'IBM' and date > DATE_SUB(CURDATE(), INTERVAL 3 DAY) order by date desc limit 1));

//Eventum #146
function isadvancement( $symbol, $days, $volatilitypercent = 1 )
{
	if( percentadvancement( $symbol, $days ) > $volatilitypercent )
		return 1;
	else
		return 0;
}
//!146

function percentadvancement( $symbol, $days )
{
//How much advancement for a symbol in days 

	require_once( MODELDIR . '/include_all.php' );
	require_once( MODELDIR . '/stockprices.class.php' );
	$stockprices = new stockprices;
       
	//$minlow = "select min(day_close) as low from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
	$minlow = "select min(day_low) as low from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
        $stockprices->querystring = $minlow;
        $stockprices->GenericQuery();
        if( isset( $stockprices->resultarray[0]['low'] ))
                $low = $stockprices->resultarray[0]['low'];
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
                //var_dump( $low );
        }
        else
        {
                unset( $stockprices );
                return "-102";
        }
	if( $low <> 0)
		$percentadvancement = ($today/$low - 1) * 100;
	else
		$percentadvancement = 0;
	return $percentadvancement;
}

function dollaradvancement( $symbol, $days )
{
//How much advancement for a symbol in days 

   	require_once( MODELDIR . '/include_all.php' );
        require_once( MODELDIR . '/stockprices.class.php' );
        $stockprices = new stockprices;

        //$minlow = "select min(day_close) as low from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
        $minlow = "select min(day_low) as low from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( CURDATE(), INTERVAL " . $days . " DAY )";
        $stockprices->querystring = $minlow;
        $stockprices->GenericQuery();
        if( isset( $stockprices->resultarray[0]['low'] ))
                $low = $stockprices->resultarray[0]['low'];
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
                //var_dump( $low );
        }
        else
        {
                unset( $stockprices );
                return "-102";
        }



	$dollaradvancement = $today - $low;
	return $dollaradvancement;
}


//test
/*
define( 'MODELDIR', '/mnt/2/development/var/www/html/finance/model/' );
echo "Advancement of IBM is " . dollaradvancement( "IBM", "14" ) . " for a percentage of " . percentadvancement( "IBM", "14" );
*/

<?php

//20110122 KF #218 Changed select statement in volumealert as it had an extraneous , on the end.

/*

According to DOW there were 3 trends
primary - 1+ years
secondary 1-3 months
tertiary up to 3 weeks

http://www.incademy.com/courses/Technical-analysis-I/Volume-data/6/1031/10002
For most technical analysts, volume is used as corroborative evidence of a trend rather than primary evidence. There are five basic rules:

   1. When prices are going up and the volume is increasing then the trend will stay in force and prices will continue to rise.

   2. When prices are going up and the volume is decreasing the trend is unlikely to continue and prices will either increase at a slower rate or start to fall.

   3. When prices are decreasing and volume is increasing then the trend will continue and prices will fall further.

   4. When prices are decreasing and the volume is also decreasing then the trend is unlikely to continue and the decline in prices will slow down or they will start to increase.

   5. When volume is consistent, not rising or falling, then the effect on prices is neutral and you need to find some other way of backing up your trend analysis.
*/

$MODELDIR = "../../model/";
require_once( '../../local.php' );
require_once( '../../model/include_all.php' );
require_once( $MODELDIR . '/technicalanalysis.class.php' );

function volumetrend( $price0, $price1, $vol0, $vol1 )
{
	if( 
		( $vol0 > $vol1 ) 
		AND ( $price0 > $price1 )
	)
	{
		$trend = "up";
	}	
	else	
	if( 
		( $vol0 < $vol1 ) 
		AND ( $price0 > $price1 )
	)
	{
		$trend = "slowfall";
	}	
	else	
	if( 
		( $vol0 > $vol1 ) 
		AND ( $price0 < $price1 )
	)
	{
		$trend = "down";
	}	
	else	
	if( 
		( $vol0 < $vol1 ) 
		AND ( $price0 < $price1 )
	)
	{
		$trend = "slowrise";
	}	
	else
	{
		$trend = "neutral";
	}
	return $trend;
}


function volumealert( )
{
        //Going to use 12 day as close enough for 3 week
        //Using 90 day for 3 month
        //Not looking at primary trends here.
	//
	//Run through the techanalysis database
	//and look at yesterday's and today's
	//12 and 90 values for both volume
	//and price and give a "volume indicator"

	$ta = new technicalanalysis();
	$ta2 = new technicalanalysis();
	//Take care of Mon-Thurs due to date math
	$ta->where = "a.voltrendind90 not in ( 'up', 'slowfall', 'down', 'slowrise', 'neutral' ) and a.volume90 <> 0 and a.date - 1 = b.date ";
	//Only calculate since Sept
	$ta->where .= " and a.date > '2009-09-01'";
//20110122 KF #218 Remove , from pafter price261
	$ta->select = "a.symbol, a.date, a.volume26 as vol26, a.volume90 as vol90, a.expmovingaverage26 as price26, a.expmovingaverage90 as price90, b.volume26 as vol27, b.volume90 as vol91, b.expmovingaverage26 as price27, b.expmovingaverage90 as price91,  a.volume260 as vol260,  b.volume260 as vol261, a.expmovingaverage260 as price260, b.expmovingaverage260 as price261 ";
	$ta->from = "technicalanalysis a, technicalanalysis b";
	$ta->nolimit = TRUE;
//20110122 KF #218 hard coding out the orderby to see if this clears the error.  Appears that it is auto-genned anyway and I don't see a reason for order by here.
	$ta->orderby = "";
	$ta->Select();
	foreach( $ta->resultarray as $row )
	{
		$update['voltrendind26'] = volumetrend( $row['price26'], $row['price27'], $row['vol26'], $row['vol27'] );
		$update['voltrendind90'] = volumetrend( $row['price90'], $row['price91'], $row['vol90'], $row['vol91'] );
		$update['voltrendind260'] = volumetrend( $row['price260'], $row['price261'], $row['vol260'], $row['vol261'] );
		$update['symbol'] = $row['symbol'];
		$update['date'] = $row['date'];
		$ta2->Update( $update );
	}

	//Take care of the day before a mid week stat holidays
	$ta->where = "a.voltrendind90 not in ( 'up', 'slowfall', 'down', 'slowrise', 'neutral' ) and a.volume90 <> 0 and a.date - 2 = b.date ";
	//Only calculate since Sept
	$ta->where .= " and a.date > '2009-09-01'";
	$ta->nolimit = TRUE;
	$ta->Select();
	foreach( $ta->resultarray as $row )
	{
		$update['voltrendind26'] = volumetrend( $row['price26'], $row['price27'], $row['vol26'], $row['vol27'] );
		$update['voltrendind90'] = volumetrend( $row['price90'], $row['price91'], $row['vol90'], $row['vol91'] );
		$update['voltrendind260'] = volumetrend( $row['price260'], $row['price261'], $row['vol260'], $row['vol261'] );
		$update['symbol'] = $row['symbol'];
		$update['date'] = $row['date'];
		$ta2->Update( $update );
	}
			
	//Take care of Fridays
	$ta->where = "a.voltrendind90 not in ( 'up', 'slowfall', 'down', 'slowrise', 'neutral' ) and a.volume90 <> 0 and a.date - 3 = b.date ";
	//Only calculate since Sept
	$ta->where .= " and a.date > '2009-09-01'";
	$ta->nolimit = TRUE;
	$ta->Select();
	foreach( $ta->resultarray as $row )
	{
		$update['voltrendind26'] = volumetrend( $row['price26'], $row['price27'], $row['vol26'], $row['vol27'] );
		$update['voltrendind90'] = volumetrend( $row['price90'], $row['price91'], $row['vol90'], $row['vol91'] );
		$update['voltrendind260'] = volumetrend( $row['price260'], $row['price261'], $row['vol260'], $row['vol261'] );
		$update['symbol'] = $row['symbol'];
		$update['date'] = $row['date'];
		$ta2->Update( $update );
	}

	//Take care of Fridays where Monday is a stat
	$ta->where = "a.voltrendind90 not in ( 'up', 'slowfall', 'down', 'slowrise', 'neutral' ) and a.volume90 <> 0 and a.date - 4 = b.date ";
	//Only calculate since Sept
	$ta->where .= " and a.date > '2009-09-01'";
	$ta->nolimit = TRUE;
	$ta->Select();
	foreach( $ta->resultarray as $row )
	{
		$update['voltrendind26'] = volumetrend( $row['price26'], $row['price27'], $row['vol26'], $row['vol27'] );
		$update['voltrendind90'] = volumetrend( $row['price90'], $row['price91'], $row['vol90'], $row['vol91'] );
		$update['voltrendind260'] = volumetrend( $row['price260'], $row['price261'], $row['vol260'], $row['vol261'] );
		$update['symbol'] = $row['symbol'];
		$update['date'] = $row['date'];
		$ta2->Update( $update );
	}
}

volumealert();
?>

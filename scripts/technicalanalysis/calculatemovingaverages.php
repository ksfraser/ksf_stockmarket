<?php

//20090814 KF
//Calculate the various moving averages for a stock
//and add into technicalanalysis

require_once( '../../model/include_all.php' );
require_once( '../../model/stockprices.class.php' );
require_once( '../../model/technicalanalysis.class.php' );
require_once( 'data/movingaverages.php' );
require_once( 'data/standarddeviation.php' );
//	$flog = fopen( "../../logs/" . __FILE__ . "-" . date( 'Y-m-d' ) . ".txt", "wt" );

function calculatemovingaverages( $startdate, $symbol, $flog = NULL )
{
	$data = array();
	$volumearray = array();
	//$interval = floor( (260 + 9) * 7 / 5) ; //260 data points converted for weeks including stat holidays in 12 months
	$interval = 365; 
	//get the stockprices for the symbol from the startdate
	$stockprices = new stockprices();
	//$stockprices->where = "date >= DATE_SUB('" . $startdate . "', INTERVAL " . $interval . " DAY) and symbol = '" . $symbol . "'";
	$stockprices->where = "date >= DATE_SUB('" . $startdate . "', INTERVAL 1 YEAR) and symbol = '" . $symbol . "'";
	$stockprices->select = "day_close, volume, date";
	$stockprices->orderby = "date asc";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	$datacount = count( $stockprices->resultarray );
/*
		if ( NULL != $flog )
			fwrite( $flog, "Symbol $symbol has $datacount rows to calculate\n" );
		else
*/
			echo "Symbol " . $symbol . " has " . $datacount . " rows to calculate\n";
	foreach( $stockprices->resultarray as $row )
	{
		$data[] = $row['day_close'];
		$volumearray = $row['volume'];
	}
	//Calculate 50  MA
		$ma50 = movingaverage( $data, "50" );
	//Calculate 200 MA
		$ma200 = movingaverage( $data, "200" );
		$ma260 = movingaverage( $data, "260" );
		$stddev260 = standarddeviation( $data, "260", $ma260 );
	//Calculate Vol MAs
		$vol260 = movingaverage( $volumearray, "260" );
		$vol90 = movingaverage( $volumearray, "90" );
		$vol26 = movingaverage( $volumearray, "26" );
		$vol12 = movingaverage( $volumearray, "12" );
	//Calculate 9  EMA
		$ma9 = exponentialmovingaverage( $data, "9" );
	//Calculate 12 EMA
		$ma12 = exponentialmovingaverage( $data, "12" );
	//Calculate 26 EMA
		$ma26 = exponentialmovingaverage( $data, "26" );
	//Calculate 90 EMA
		$ma90 = exponentialmovingaverage( $data, "90" );
	//MERGE results
	$results = array();
	for( $i = 8; $i < $datacount; $i++ )
	{
		$date =   $stockprices->resultarray[$i]['date']; 
		$results[ $date ]['date'] =  $date; 
		$results[ $date ]['symbol'] =  $symbol; 
		$results[ $date ]['expmovingaverage9'] = $ma9[$i];
		if( $i >= 49 )
			$results[ $date ]['movingaverage50'] = $ma50[$i];
		if( $i >= 89 )
			$results[ $date ]['volume90'] = $vol90[$i];
			$results[ $date ]['expmovingaverage90'] = $ma90[$i];
		if( $i >= 199 )
			$results[ $date ]['movingaverage200'] = $ma200[$i];
		if( $i >= 259 )
			$results[ $date ]['movingaverage260'] = $ma260[$i];
			$results[ $date ]['volume260'] = $vol260[$i];
			$results[ $date ]['standarddeviation260'] = $stddev260[$i];
		if( $i >= 11 )
			$results[ $date ]['expmovingaverage12'] = $ma12[$i];
			$results[ $date ]['volume12'] = $vol12[$i];
		if( $i >= 25 )
		{
			$results[ $date ]['volume26'] = $vol26[$i];
			$results[ $date ]['expmovingaverage26'] = $ma26[$i];
			$results[ $date ]['momentumoscillator'] =  $ma12[$i] - $ma26[$i]; 
			$results[ $date ]['priceoscillator'] =  ($ma12[$i] - $ma26[$i]) / $ma26[$i]; 
			$results[ $date ]['macd_histogram'] =  $ma12[$i] - $ma26[$i] - $ma9[$i];
		}
	}	
	unset( $stockprices );
	return $results;
}

//function tamovingaverages( $startdate, $flog = NULL )
function tamovingaverages( $startdate )
{
	$stockprices = new stockprices();
	$stockprices->select = "distinct symbol";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	foreach( $stockprices->resultarray as $row )
	{
/*
		if ( NULL != $flog )
			fwrite( $flog, "Symbol $row['symbol'] with start date $startdate\n" );
		else
*/
	//	var_dump( $row );
			echo "Symbol " .  $row['symbol'] . " with start date $startdate\n";
		$ma = calculatemovingaverages( $startdate, $row['symbol'] );
		//Add into technicalanalysis but candlestick data 
			//might already be there, so update
			//rather than insert
		$ta = new technicalanalysis();
		$ta->fieldspec['idtechnicalanalysis']['prikey'] = 'N';
		$ta->fieldspec['date']['prikey'] = 'Y';
		$ta->fieldspec['symbol']['prikey'] = 'Y';
		$ta->UpdateArray( $ma );
		unset( $ma ); //20111210 free more memory in case it keeps allocated more rather than writing over top...
	}
	unset( $stockprices );
}	


function av_unittest()
{
//TEST
//1
//	$res = calculatemovingaverages( "2009-01-01", "IBM", $flog );
//	var_dump( $res );
//2
	tamovingaverages( "2011-01-01" );
	//tamovingaverages( "2011-01-01", $flog );
}

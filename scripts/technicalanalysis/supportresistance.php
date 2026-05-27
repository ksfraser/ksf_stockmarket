<?php

//20090815 KF
//	Support and resistance levels
//
//	A support level is the price at which no investor wants to sell for less than
//	A resistance level is the price that no investor wants to pay more than for the stock.

//support12, support26, resistance12, resistance26

require_once( '../../model/include_all.php' );
require_once( '../../model/stockprices.class.php' );
require_once( '../../model/technicalanalysis.class.php' );

function calcsupportresistance( $data, $symbol, $date )
{
//	var_dump( $data );
	//echo "Symbol $symbol on date $date\n";
	
	$count = 0;
	$max = 0;
	$min = 99999999999999;
	foreach( $data as $row )
	{
		if( $row['day_high'] > $max )
			$max = $row['day_high'];
		if( $row['day_low'] < $min )
			$min = $row['day_low'];
		$count++;
		if( $count == 12 )
		{
			$result['resistance12'] = $max;
			$result['support12'] = $min;
		}
	}
	$result['resistance26'] = $max;
	$result['support26'] = $min;
	$result['symbol'] = $symbol;
	$result['date'] = $date;
	//var_dump( $result );
	return $result;
}

function sr_calc( $symbol, $startdate )
{
	$stockprices = new stockprices();
	$stockprices->select = "date, day_low, day_high";
	$stockprices->orderby = "date desc";
	$stockprices->where = "symbol = '" . $symbol . "' and date >= DATE_SUB( '" . $startdate . "', INTERVAL 27 DAY )";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	
	$count = count( $stockprices->resultarray );
	//var_dump( $stockprices->resultarray );
	for( $j = 0; $j < $count - 26; $j++ )
	{
		for( $i = 0; $i < 26; $i++ )
		{
			$data[$i] = $stockprices->resultarray[ $j + $i ];
		}
		$date = $stockprices->resultarray[ $j ]['date'];
		$res[ $j ] = calcsupportresistance( $data, $symbol, $date );
		//var_dump( $res );
		return $res;
	}
}

function supportresistance( $startdate )
{
	$ta = new technicalanalysis();
	$ta->fieldspec['date']['idtechnicalanalysis'] = 'N';
	$ta->fieldspec['date']['prikey'] = 'Y';
	$ta->fieldspec['symbol']['prikey'] = 'Y';
	$stockprices = new stockprices();
	$stockprices->select = "distinct symbol";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	foreach( $stockprices->resultarray as $row )
	{
		//var_dump( $row );
		$res = sr_calc( $row['symbol'], $startdate );
		var_dump( $res );
		$ta->UpdateArray( $res );
		var_dump( $ta->querystring );
	}
}

//TEST
//2
	//var_dump( sr_calc( "IBM", "2009-06-01" ) );
//3
	supportresistance( "2009-01-01" );	
	


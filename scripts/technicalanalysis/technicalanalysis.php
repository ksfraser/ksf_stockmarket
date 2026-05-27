<?php

//20090816 KF
//Create a library of functions that are performed for Technical Analysis.

/*********************************************************
*
*	This script written on the assumption
*	that the checkcandlestick script
*	has already been run.  The checkcandlestick
*	script adds a row for each stock/date/candlestick
*	combination.  We want to update each row.
*********************************************************/

require_once( '../../local.php' );
require_once( '../../model/include_all.php' );
require_once( '../../model/stockprices.class.php' );
require_once( '../../model/technicalanalysis.class.php' );
require_once( 'data/movingaverages.php' );
require_once( 'data/statistics.php' );
require_once( 'calculatemovingaverages.php' );

//	Support and resistance levels
//
//	A support level is the price at which no investor wants to sell for less than
//	A resistance level is the price that no investor wants to pay more than for the stock.

//support12, support26, resistance12, resistance26

//Volume is the average trading volume in the period
//volume12, volume26

//Price Change Percent is the percentage change in closing price from the previous day

//Relative Strength Index
//RSI = 100 - (100/ (1-RS) )
//where RS = Average of x days' up closes / Average of x days' down closes. 
//The original author used 14 days but now it is common
//to use 9 or 26, similar to MACD
//When RSI approaches 70, it is considered overbought.  (Therefore sell)
//When RSI approaches 30, it is considered oversold.    (Therefore buy)
//The RSI works best with volatile shares, not quiet shares.
//This is a trailing indicator.

//RSI oscillator is the RSI / max(RSI) for a period (i.e. 26 days).  This becomes a leading
//indicator - -.8 and +.8 are the oversold/overbought values.

//Bollingerbands address trends

//Commodity Channel Index
/*
 There are 4 steps involved in the calculation of the CCI:

      Calculate the last period's Typical Price (TP) = (H+L+C)/3 where H = high, L = low, and C = close.
      Calculate the 20-period Simple Moving Average of the Typical Price (SMATP).
      Calculate the Mean Deviation. First, calculate the absolute value of the difference between the last period's SMATP and the typical price for each of the past 20 periods. Add all of these absolute values together and divide by 20 to find the Mean Deviation.
      The final step is to apply the Typical Price (TP), the Simple Moving Average of the Typical Price (SMATP), the Mean Deviation and a Constant (.015) to the following formula:

CCI = ( Typical Price - SMATP ) / ( .015 X Mean Deviation )

The CCI typically oscillates above and below a zero line. Normal oscillations will occur within the range of +100 and -100. Readings above +100 imply an overbought condition, while readings below -100 imply an oversold condition. As with other overbought/oversold indicators, this means that there is a large probability that the price will correct to more representative levels.

The CCI typically oscillates above and below a zero line. Normal oscillations will occur within the range of +100 and -100. Readings above +100 imply an overbought condition, while readings below -100 imply an oversold condition. As with other overbought/oversold indicators, this means that there is a large probability that the price will correct to more representative levels.
*/

//MACD related values
//MACD = expMA12 - expMA26 (otherwise known as momentumoscillator
//Price Oscillator = MACD / expMA12
//MACD Histogram =  MACD - trigger line (EMA9)
//MA crossovers
//MA centreline crossovers
//MA Momentum - change in MA values.  + is bullish, - is bearish

//stochastic

//Linear Regression (slope. angle, intercept)

//Candlesticks and Heikan Ashi candlesticks handled in a separate file


function calculate( $data, $symbol, $date, $averages )
{
	$count = 0;
	$resistance = 0;
	$support = 99999999999999;
/* 20090821 KF Covered in calculatemovingaverages
	$volumesum = 0;
*/
	$todayclose = -1;
  	$upcount = 0;
        $downcount = 0;
        $upsum = 0;
        $downsum = 0;
	$daysum = 0;
	$percentage9 = ( 2 / ( 9 + 1 ) );
	$percentage12 = ( 2 / ( 12 + 1 ) );
	$percentage26 = ( 2 / ( 26 + 1 ) );
	$typicalprice = 0;
	
//echo __LINE__ . "\n";
	foreach( $data as $row )
	{
		//echo __LINE__ . "\n";
		if( $row['day_high'] > $resistance )
			$resistance = $row['day_high'];
		if( $row['day_low'] < $support )
			$support = $row['day_low'];
		$yesterdayclose = $row['day_close'];
		$daysum += $row['day_close'];
/* 20090821 KF Covered in calculatemovingaverages
		$volumesum += $row['volume'];
*/
		if( $todayclose > 0 )
		{
		//echo __LINE__ . "\n";
			if( $todayclose >= $yesterdayclose )
			{
		//echo __LINE__ . "\n";
				$upsum += $todayclose;
				$upcount++;
			}
			else
			{
		//echo __LINE__ . "\n";
				$downsum += $todayclose;
				$downcount++;
			}
		}
		$count++;
		$typicalprice = ( $row['day_high'] + $row['day_low'] + $row['day_close'] ) / 3;
		$tpdevsum = 0;
		if( $count < 21 )
		{
		//echo __LINE__ . "\n";
			//need 20 days of TP
			$typicalpricearray[$count - 1] = $typicalprice;
			$close[] = $row['day_close'];
		}
		else if( $count == 21 )
		{
		//echo __LINE__ . "\n";
/*
			$stats = new statistics( $typicalprice );
			$stats->calculate();
			$matp = $stats->movingaverage( 20 );
			$tpstandarddeviation = $stats->getstandarddeviation();
*/
			$matp = movingaverage( $typicalprice, 20 );
			foreach( $typicalpricearray as $row )
			{
				$tpdevsum += abs($row - $matp);
			}
			$tpstandarddeviation = $tpdevsum / 20; 
	
			$result['commoditychannelindex'] = 
				( $typicalprice - $matp ) 
				/ ( 0.015 * $tpstandarddeviation );
		}
	//Since we are loopoing through an array of data to calculate values for one day
	//and the values are date desc it is the first value that is for that day
		if( $count == 1 )
		{
		//echo __LINE__ . "\n";
			$result['typicalprice'] = $typicalprice ;
		}
		if( $count == 2 )
		{
		//echo __LINE__ . "\n";
			//data is in newest first order, so when count =2 
			//todayclose (set at end of count = 1) has the
			//appropriate data
			$result['pricechangepercent'] = 100 * ( $todayclose - $yesterdayclose ) / $yesterdayclose;
			$result['day_close'] = $yesterdayclose;
		}
		if( $count == 12 )
		{
		//echo __LINE__ . "\n";
			$result['resistance12'] = $resistance;
			$result['support12'] = $support;
/* 20090821 KF Covered in calculatemovingaverages
			$result['volume12'] = $volumesum / 12;
*/
		}
		if( $count == 26 )
		{
		//echo __LINE__ . "\n";
			$closedevsum = 0;
			$result['resistance26'] = $resistance;
			$result['support26'] = $support;
/* 20090821 KF Covered in calculatemovingaverages
			$result['volume26'] = $volumesum / $count;
*/
			if( $downcount == 0 )
				$downcount = 1;
			if( $upcount == 0 )
				$upcount = 1;
			$denom = ( $downsum / $downcount );
			if( $denom != 0 )
				$rs =  ($upsum / $upcount) / $denom;
			else
				$rs = 0.5; //Right in the middle
			$result['relativestrenghtindex'] = 100 - (100 / (1 + $rs ));
/* 20090821 KF Covered in calculatemovingaverages
			$result['expmovingaverage26'] = $ema26;
*/
			//var_dump( $close );
 			$closema = movingaverage( $close, $count );
                        foreach( $close as $row )
                        {
                                $closedevsum += abs($row - $closema);
                        }
                        $closedev = $closedevsum / $count;
			$result['bollingerbandmiddle'] = $daysum / $count;
			$result['bollingerbandupper'] = $daysum / $count + 2 * $closedev;
			$result['bollingerbandlower'] = $daysum / $count - 2 * $closedev;
			$bbdenom = $result['bollingerbandupper'] - $result['bollingerbandlower'];
			$result['bollingerpercentb'] = $row['day_close'] - $result['bollingerbandlower'] / $bbdenom;
			$result['bollingerbandwidth'] = $bbdenom / $result['bollingerbandmiddle'];
			$result['coefficientofvariation'] = $result['bollingerbandwidth'] / 4;
		}
		$todayclose = $row['day_close'];
	}
	$result['symbol'] = $symbol;
	
	$result['date'] = $date;
	return $result;
}

function sr_calc( $symbol, $startdate, $averages )
{
		//echo __LINE__ . "\n";
	$res = array();
	//$interval = floor( 27 * 7 / 5 ); //26 days + 1 stat in that time period, transformed to include weekends when getting the date
	$interval = 365; //260 working days
	$stockprices = new stockprices();
	//By not taking specific columns, we can calculate volume, etc as well.
	//$stockprices->select = "date, day_low, day_high";
	$stockprices->orderby = "date desc";
	$stockprices->where = "symbol = '" . $symbol . "' and date >= DATE_SUB( '" . $startdate . "', INTERVAL " . $interval . " DAY )";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	
	$count = count( $stockprices->resultarray );
	//var_dump( $stockprices->resultarray );
	//we are using the 260 in the next 2 loops to limit the calculations to the start date
	for( $j = 0; $j < $count - 260; $j++ )
	{
		//echo __LINE__ . "\n";
		for( $i = 0; $i <= 260; $i++ )
		{
			//echo __LINE__ . "\n";
			$data[$i] = $stockprices->resultarray[ $j + $i ];
		}
		$date = $stockprices->resultarray[ $j ]['date'];
		$res[ $j ] = calculate( $data, $symbol, $date, $averages );
		//var_dump( $res );
	}
	unset( $stockprices );
	var_dump( $res[0] );
	return $res;
}

function technicalanalysis( $startdate )
{
	$ta = new technicalanalysis();
	$ta->fieldspec['date']['idtechnicalanalysis'] = 'N';
	$ta->fieldspec['date']['prikey'] = 'Y';
	$ta->fieldspec['symbol']['prikey'] = 'Y';
	$stockprices = new stockprices();
	$stockprices->select = "distinct p.symbol";
	$stockprices->from = "stockprices p, technicalanalysis t";
	$stockprices->where = "t.expmovingaverage26 = 0 and t.symbol = p.symbol and t.date >= '" . $startdate . "'";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	foreach( $stockprices->resultarray as $row )
	{
		//echo __LINE__ . "\n";
		echo $row['symbol'] . " with startdate $startdate\n";
		$averages = calculatemovingaverages( $startdate, $row['symbol'] );
                $ta->fieldspec['idtechnicalanalysis']['prikey'] = 'N';
                $ta->fieldspec['date']['prikey'] = 'Y';
                $ta->fieldspec['symbol']['prikey'] = 'Y';
		$ta->InsertArray( $averages );
		$insertmissing = 1;
		$ta->UpdateArray( $averages, $insertmissing );
		$res = sr_calc( $row['symbol'], $startdate, $averages );
		$ta->UpdateArray( $res, $insertmissing );
	}
	return SUCCESS;
}

technicalanalysis( "2010-01-03" );
/*
	$ta = new technicalanalysis();
	$arr = sr_calc( "IBM", "2011-01-01", 1 );
	$ta->InsertArray( $arr );
	$ta->UpdateArray( $arr );
*/
?>


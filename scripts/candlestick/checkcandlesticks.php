<?php

//20090717 KF Candlestick analysis
//ta-lib has functions to do all of the candlestick analysis.

//In the mean time, most of the formulaes looked to need up to 4 days of data

require_once( '../../model/include_all.php' );
require_once( 'candlesticks2.php' );
require_once( '../../model/stockprices.class.php' );
require_once( '../../model/technicalanalysis_candlesticks.class.php' );
require_once( '../../model/candlesticksoccured.class.php' );
require_once( '../../model/candlestickdates.class.php' );

global $APPDIR;

$stockprices = new stockprices();
$dates = new stockprices();
$candlestickdates = new candlestickdates();
$technicalanalysis_candlesticks = new technicalanalysis_candlesticks();
$candlestickdates = new candlestickdates();
$candlesticksoccured = new candlesticksoccured();

$filename =  $APPDIR . "/logs/checkcandlestick." . date( 'Ymdhms' ) . ".txt";
$flog = fopen( $filename, "w" );
echo "Opened $filename \n";

/*****************************************
*	Get the last date candlesticks
*	have been checked.
*************************************** */
$dates->querystring = "select max( candlestickdates ) as maxdate from candlestickdates";
$dates->GenericQuery();
$lastdate = $dates->resultarray[0]['maxdate'];
$dates->querystring = "select max( date ) as maxdate from stockprices";
$dates->GenericQuery();
echo "Latest date in stockprices: " . $dates->resultarray[0]['maxdate'] . "\n";;
if( NULL != $flog )
	fwrite( $flog, "Latest date in stockprices: " . $dates->resultarray[0]['maxdate'] . "\n" );

/*************************************
*	Get the last date of data we 
*	have in the stock prices table
*
*	Grab dates in ascending order
*	So that if this script errors
*	out due to memory etc the oldest
*	dates are calculated first
************************************ */
$dates->querystring = "select distinct date as candlestickdates from stockprices where date >= DATE_SUB( '" . $lastdate . "', INTERVAL 6 DAY ) order by date asc"; //Grab last dates
$dates->GenericQuery();
//20090917 KF subtracting 4 results in the last 4 days not being dealt with
//$stop = count( $dates->resultarray ) - 4;
$stop = count( $dates->resultarray );
echo "Count of dates: $stop\n";
if( NULL != $flog )
	fwrite( $flog, "Count of dates: $stop\n" );
if( $stop <= 0 )
	exit(0);

//var_dump ($dates->resultarray);

$today = date( 'Y-m-d h:m:s' );
$datearray = array();


/*********************************
*	Get the data for the
*	dates between last date
*	processed and last date
*	we have price data for
*
*	This will calculate one date at
*	a time for ALL stocks that have
*	price data on the date and 3 
*	preceding dates
*********************************/
for( $start = 3; $start < $stop; $start++ )
{

	$stockprices->querystring = " select 
		a.symbol as symbol, 
		a.date as date, 
		a.day_open as open, 
		a.day_low as low, 
		a.day_high as high, 
		a.day_close as close, 
		a.volume as volume, 
		b.day_open as open1, 
		b.day_low as low1, 
		b.day_high as high1, 
		b.day_close as close1, 
		b.volume as volume1, 
		c.day_open as open2, 
		c.day_low as low2, 
		c.day_high as high2, 
		c.day_close as close2, 
		c.volume as volume2, 
		d.symbol as symbol3, 
		d.day_low as low3, 
		d.day_high as high3, 
		d.day_close as close3, 
		d.volume as volume3 
	from 	stockprices a, 
		stockprices b, 
		stockprices c, 
		stockprices d 
	where	a.symbol = b.symbol
		AND a.symbol = c.symbol
		AND a.symbol = d.symbol
		AND a.date = '" . $dates->resultarray[$start - 0]['candlestickdates'] . "'
		AND b.date = '" . $dates->resultarray[$start - 1]['candlestickdates'] . "'
		AND c.date = '" . $dates->resultarray[$start - 2]['candlestickdates'] . "'
		AND d.date = '" . $dates->resultarray[$start - 3]['candlestickdates'] . "'
	";

	$stockprices->GenericQuery();
	$count = 0;
	echo "Count of rows of stock prices to check: " . count( $stockprices->resultarray ) . " on date " . $dates->resultarray[$start - 0]['candlestickdates'] . "\n";
	if( NULL != $flog )
		fwrite( $flog, "Count of rows of stock prices to check: " . count( $stockprices->resultarray ) . " on date " . $dates->resultarray[$start - 0]['candlestickdates'] . "\n" );
	foreach( $stockprices->resultarray as $row )
	{
	//	var_dump( $row );
		/***************************************
		*	candlestick takes a row of data
		*	and compares it against all 
		*	candlestick patterns that we
		*	have included in the library
		*
		*	Result is the list of candlesticks
		*	that match that pattern.  A pattern
		*	can match multiple candlesticks
		*	especially the DOJI family
		*
		*	Need to do further analysis of this
		*	multiple match to see if there is
		*	certain patterns so that we can
		*	reduce the compares.  Is there a
		*	priority that can be established
		*	when multiples appear that better
		*	indicate the sentiments of the 
		*	market.  I can't see this not having
		*	been researched by others.
		***************************************/
		$result = candlestick( $row );
		//var_dump( $result );
		foreach ( $result as $symbol => $value )
		{
			$insert['symbol'] = $symbol;
			foreach ( $value as $date => $v )
			{
				$insert['date'] = $date;
				$datearray['candlestickdates'] = $date;
				foreach( $v as $candle => $exp )
				{
					$insert['candlestick'] = $candle;
					$insert['explanation'] = $exp;
					$insert['createddate'] = $today;
					//var_dump( $insert );
					$technicalanalysis_candlesticks->Insert( $insert );
					$candlesticksoccured->Insert( $insert );
					if( NULL != $flog )
						fwrite( $flog, "TA insert: " . $technicalanalysis_candlesticks->querystring . "\n" );
					//20100817 KF Removing the errorlog as it is just showing blank data failing validation.
					//Perhaps I should really change the logging of the data failing on null fields.
					//fwrite( $flog, "TA errors:\n" );
					//foreach( $technicalanalysis_candlesticks->errors as $line )
					//	fwrite( $flog, $line . "\n" );
					$candlestickdates->Insert( $datearray );
					$datearray['candlestickdates'] = NULL;
					if( NULL != $flog )
						fwrite( $flog, "Candlestickdates insert: " . $candlestickdates->querystring . "\n" );
					//var_dump( $technicalanalysis_candlesticks->errors );
					/**************************************
					*	Free up memory since we
					*	tend to run on smaller machines
					*************************************/
					unset( $technicalanalysis_candlesticks->errors );
					//What is $email used for again?
					//$email[$count] = $insert;
					$count++;
				}
			}
		}
		//20101122 KF unset variables so that maybe this proc won't
		//keep dying due to max memory exceeded
		unset( $stockprices->errors );
	}
	//20101122 KF unset variables so that maybe this proc won't
	//keep dying due to max memory exceeded
	unset( $stockprices->resultarray );
}
unset( $technicalanalysis_candlesticks );

//unset( $candlestickdates->errors );
//$candlestickdates->querystring = "insert ignore into candlestickdates (candlestickdates) select date from stockprices where date between '" . $lastdate . "' and '" . $date . "'";
//var_dump( $candlestickdates->querystring );
//$candlestickdates->GenericQuery();
//var_dump( $email );
//$candlestickdates->InsertArray( $datearray );
//var_dump( $candlestickdates->errors );
?>

<?php

//20090814 KF
//Relative Strength Index

/*

RSI = 100 - (100/ (1-RS) )

where RS = Average of x days' up closes / Average of x days' down closes.  
The original author used 14 days but now it is common
to use 9 or 26, similar to MACD

When RSI approaches 70, it is considered overbought.  (Therefore sell)
When RSI approaches 30, it is considered oversold.    (Therefore buy)

The RSI works best with volatile shares, not quiet shares.

*/

require_once( '../../model/include_all.php' );
require_once( '../../model/stockprices.class.php' );
require_once( '../../model/technicalanalysis.class.php' );

function calculateRS( $data, $days )
{
	//Data needs to come in order from 
	//newest to oldest for the 
	//number days to work

//	var_dump( $data );
	$upcount = 0;
	$downcount = 0;
	$upsum = 0;
	$downsum = 0;
	for( $i = 0; $i < $days; $i++ )
	{
		if( $data[$i] > $data[$i + 1] )
		{
			//echo $data[$i] . " is greater than " . $data[$i + 1] . "\n";
			$upsum += $data[$i];
			$upcount++;
		}
		else
		if( $data[$i] < $data[$i + 1] )
		{
			//echo $data[$i] . " is less than " . $data[$i + 1] . "\n";
			$downsum += $data[$i];
			$downcount++;
		}
		else
		if( $i < ($days - 2) AND $data[$i] > $data[$i + 2] )
		{
			//echo $data[$i] . " is greater than " . $data[$i + 2] . "\n";
			$upsum += $data[$i];
			$upcount++;
		}
		else
		if( $i < ($days - 2) AND $data[$i] < $data[$i + 2] )
		{
			//echo $data[$i] . " is less than " . $data[$i + 2] . "\n";
			$downsum += $data[$i];
			$downcount++;
		}
		else
		{
			//echo $data[$i] . " is greater than " . $data[$i + 1] . "\n";
			$upsum += $data[$i];
			$upcount++;
		}
	}
	if( $downcount == 0 )
		$downcount = 1;
	$denom = ( $downsum / $downcount );
	if( $denom == 0 )
		$denom = 1;
	if( $upcount == 0 )
		$upcount == 1;
	$rs =  ($upsum / $upcount) / $denom ;
	//echo "Upsum $upsum :: $upcount :: Downsum $downsum :: $downcount \n";
	//echo " UpAve " . $upsum / $upcount . ":: DownAve " . $downsum / $downcount . ":: RS $rs \n";
	return $rs;

}

function relativestrengthindex( $symbol, $enddate, $flog = NULL )
{

	$stockprices = new stockprices();
	$stockprices->orderby = "date desc";
	$stockprices->where = "symbol = '" . $symbol . "' and date <= '" . $enddate . "'";
	$stockprices->limit = "30"; //Take a few extra data elements
	$stockprices->Select();
	foreach( $stockprices->resultarray as $row )
	{
		$data[] = $row['day_close'];
	}

	$rs9 = calculateRS( $data, 9 );
	$rs14 = calculateRS( $data, 14 );
	$rs26 = calculateRS( $data, 26 );

//	RSI = 100 - (100/ (1+RS) )
//	$rsi9 = 100 - (100 / (1 + $rs9 ));
	$rsi14 = 100 - (100 / (1 + $rs14 ));
//	$rsi26 = 100 - (100 / (1 + $rs26 ));
	return $rsi14;
}

function rsi_all_dates()
{
	//Go through tradedates and list of symbols
	//and calculate the RSI.  Then update
	//techanalysis with the results
	$stockprices = new stockprices();
	$stockprices2 = new stockprices();
	$stockprices->select = "distinct symbol";
//	$stockprices->where = "symbol = 'IBM'";
	$stockprices->nolimit = TRUE;
	$stockprices->Select();
	foreach( $stockprices->resultarray as $row )
	{
		$stockprices2->orderby = "date desc";
		$stockprices2->where = "symbol = '" . $row['symbol'] . "'";
		$stockprices2->nolimit = TRUE;
		$stockprices2->Select();
		$rescount = count( $stockprices2->resultarray );
	//	echo "Have $rescount rows for " . $row['symbol'] . "\n";
	//	sleep(1);
		foreach( $stockprices2->resultarray as $row )
		{
			$data[] = $row['day_close'];
		}
		for( $i = 0; $i < $rescount; $i++)
		{
		//	echo "I count is $i.  Send data for " . $stockprices2->resultarray[$i]['date'] . "\n";
			for( $j = 0; $j < 15; $j++ )
			{
				$rsdata[$j] = $data[ $i + $j ];
			}
		//	echo "First data " . $rsdata[0] . "\n";
			$rsi[$i]['relativestrengthindex'] = 100 - (100 / (1 + calculateRS( $rsdata, 14 ) ));
			$rsi[$i]['symbol'] = $row['symbol'];
			$rsi[$i]['date'] = $stockprices2->resultarray[$i]['date'];
			unset( $rsdata );
		//	var_dump( $rsi[$i] );
		}
	}
	return $rsi;
}

function rsi_oscillator( $rsiarray )
{
	$rsicount = count( $rsiarray );
	if( $rsicount < 1 )
	{
		return NULL;
	}
	$max = 0;
	for( $i = 0; $i < $rsicount; $i++ )
	{
		if( $rsiarray[$i]['relativestrengthindex'] > $max )
			$max = $rsiarray[$i]['relativestrengthindex'];
	}
	for( $i = 0; $i < $rsicount; $i++ )
	{
		$rsiarray[$i]['rsioscillator'] = $rsiarray[$i]['relativestrengthindex'] / $max;
	}
	return $rsiarray;
}
		

function rsi2technicalanalysis()
{
	$rsi = rsi_all_dates();
	$res = rsi_oscillator( $rsi );
	$ta = new technicalanalysis();
	$ta->fieldspec['idtechnicalanalysis']['prikey'] = 'N';
	$ta->fieldspec['idtechnicalanalysis']['symbol'] = 'Y';
	$ta->fieldspec['idtechnicalanalysis']['date'] = 'Y';
	$ta->UpdateArray( $res );
}
//TEST
//$res = relativestrengthindex( "IBM", "2009-08-01" );
//echo "RSI for IBM is $res\n";

rsi2technicalanalysis();

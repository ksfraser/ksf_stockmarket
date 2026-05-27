<?php

/***************************************************************************
*
*	Depends on the stock prices being up to date for the stocks
*
*
****************************************************************************/
//20100824 KF
//Eventum 217 undefined offset 
//20090808 KF
//Eventum 162 Create heikan ashi candlestick values

//Heikin Ashi candlesticks are modified.
        //      xClose = (Open+High+Low+Close)/4
        //      o Average price of the current bar

        //      xOpen = [xOpen(Previous Bar) + Close(Previous Bar)]/2
        //      o Midpoint of the previous bar

        //      xHigh = Max(High, xOpen, xClose)
        //      o Highest value in the set

        //      xLow = Min(Low, xOpen, xClose)
        //      Lowest value in the set


/*
function max( $v1, $v2 )
{
	if( $v1 >= $v2 )
		return $v1;
	else
		return $v2;
}

function min( $v1, $v2 )
{
	if( $v1 <= $v2 )
		return $v1;
	else
		return $v2;
}
*/

require_once( '../../model/include_all.php' );

function h_close( $open, $high, $low, $close , $prevopen, $prevclose )
{
	return ( $open + $high + $low + $close ) /4;
}

function h_open( $open, $high, $low, $close , $prevopen, $prevclose )
{
	return ( $prevopen + $prevclose ) / 2;
}

function h_high( $open, $high, $low, $close , $prevopen, $prevclose )
{
	return max( $high, 
			max( 	h_open( $open, $high, $low, $close , $prevopen, $prevclose ), 
				h_close( $open, $high, $low, $close , $prevopen, $prevclose ) 
			)
		);
}

function h_low( $open, $high, $low, $close , $prevopen, $prevclose )
{
	return min( 	$high, 
			min( 	h_open( $open, $high, $low, $close , $prevopen, $prevclose ), 
				h_close( $open, $high, $low, $close , $prevopen, $prevclose ) 
			)
		);
}

function fill_heikanashi( $startdate, $enddate )
{
//20100817 KF Add a check for the last date we have data for
//so we don't recalc every time.
	if( require_once( '../../model/heikanashi.class.php' ) )
		$heikanashi = new heikanashi();
	else
		return FAILURE;
//!20100817
	$godate = $startdate;
	//Get all symbols
	if( require_once( '../../model/stockprices.class.php' ))
	{
		$stockprices = new stockprices();
		$stockprices->select = "distinct symbol";
		$stockprices->nolimit = TRUE;
		$stockprices->Select();
		foreach( $stockprices->resultarray as $row )
		{
		//20100817 KF Alter startdate depending on when this was last run for the stock
			$heikanashi->where = "symbol = '" . $row['symbol'] . "'";
			$heikanashi->select = "date";
			$heikanashi->orderby = "date desc";
			$heikanashi->limit = "2";
			$heikanashi->Select();
		//	var_dump(  $heikanashi->resultarray );
//20100825 KF 217 undefined offset
//Adding if isset
			if (isset( $heikanashi->resultarray[1]['date'] ))
				$datadate = $heikanashi->resultarray[1]['date'];
			else
				$datadate = $startdate;
//!217
			if( $datadate > $startdate )
				$godate = $datadate;
			else
				$godate = $startdate;
		//	echo "Using date " . $godate;
		//!20100817
			create_heikanashi( $row['symbol'], $godate, $enddate );
		}
		return SUCCESS;
	}
	else
	{
		echo "Couldn't get list of stocks to run";
		return FAILURE;
	}
}

function create_heikanashi( $symbol, $startdate, $enddate )
{
	if( require_once( '../../model/heikanashi.class.php' ) )
		$heikanashi = new heikanashi();
	else
		return FAILURE;
	//echo "created heikanashi object\n";
	if( require_once( '../../model/stockprices.class.php' ))
	{
		$stockprices = new stockprices();
		$stockprices->where = "date between '" . $startdate . "' and '" . $enddate . "' and symbol = '" . $symbol . "'";
		$stockprices->orderby = "date asc";
		$stockprices->nolimit = TRUE;
		$stockprices->Select();
		$rowcount = 0;
		foreach( $stockprices->resultarray as $row )
		{
			if( $rowcount > 0 )
			{
				$insert['day_open'] = h_open( $row['day_open'], $row['day_high'], $row['day_low'], $row['day_close'], $prevopen, $prevclose );
				$insert['day_close'] = h_close( $row['day_open'], $row['day_high'], $row['day_low'], $row['day_close'], $prevopen, $prevclose );
				$insert['day_high'] = h_high( $row['day_open'], $row['day_high'], $row['day_low'], $row['day_close'], $prevopen, $prevclose );
				$insert['day_low'] = h_low( $row['day_open'], $row['day_high'], $row['day_low'], $row['day_close'], $prevopen, $prevclose );
				$insert['symbol'] = $row['symbol'];
				$insert['date'] = $row['date'];
				//var_dump( $insert );
				$heikanashi->Insert( $insert );
				$prevopen = $row['day_open'];
				$prevclose = $row['day_close'];
			}
			else
			{
				$prevopen = $row['day_open'];
				$prevclose = $row['day_close'];
				$rowcount++;
			}
		}
	return SUCCESS;
	}
	else
	{
		return FAILURE;
	}
}


//TEST
//create_heikanashi( "IBM", "2009-06-01", "2009-08-06" );

fill_heikanashi( "2009-08-01",  date( 'Y-m-d' ) );

?>

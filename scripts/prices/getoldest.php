<?php

require_once( 'data/generictable.php' );
include( $MODELDIR . '/stockprices.class.php' );
//require_once( 'common/cleanstockprices.php' );
//require_once( 'common/webpage2txt.php' );
//require_once( 'common/yahooexchanges.php' );

//Define some constants
$const_YEAR = "1970";
$const_MONTH = "1";
$const_DAY = "01";

function getoldest( $flog, $thisex )
{
global $const_YEAR;
global $const_MONTH;
global $const_DAY;
	/*20090705 KF
	*What about the stocks that were partially inserted because 
	*the memory of the server was tapped out and the mysql
	*process terminated?  We need to go and find the first
	* entry (oldest) since the csv files are newest at the
	*top which means the newest get entered.  Use the oldest
	*as the end dates against 1980.
	*/
	fwrite( $flog, "\n\nSTARTING download of older data\n" );
	cleanstockprices();
	$stockprices = new stockprices();
	$stockprices->querystring = "
	SELECT p.symbol as stocksymbol, min( p.date ) as date, 
	YEAR(min( p.date )) as year, MONTH(min( p.date )) as month, DAY(min( p.date )) as day, 
	i.stockexchange as stockexchange, i.idstockinfo as idstockinfo
	FROM stockprices p, stockinfo i
	where p.symbol = i.stocksymbol
	GROUP BY p.symbol";

	$stockprices->GenericQuery();
	foreach( $stockprices->resultarray as $key => $value )
	{
	//	var_dump( $value );
		$symbol = $value['stocksymbol'];
		$idstockinfo = $value['idstockinfo'];
		if ( ($symbol != 'CASH')
			AND ($value['year'] >= $const_YEAR)
			AND ($value['month'] >= $const_MONTH)
			AND ($value['day'] >= $const_DAY)
		   )
		{
			$filename = QueryYahoo( $symbol, $thisex[ $value['stockexchange'] ] 
						,$const_YEAR, $value['year'], 
						$const_MONTH, $value['month'] - 1, 
						$const_DAY, $value['day'] - 1,
						$flog
						);
			//extractinsert( $flog, $filename, $symbol, $value );
		}
	}
	unset( $stockprices );
	return SUCCESS;
}

?>

<?php
echo __FILE__;

require_once( '../local.php' );
require_once( 'data/generictable.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
include_once( $MODELDIR . '/stockprices.class.php' );
include_once( $MODELDIR . '/stockinfo.class.php' );
include_once( $MODELDIR . '/stockexchange.class.php' );
include_once( 'view/class.genericpage.php' );
require_once( $MODELDIR . '/tradedates.class.php' );
require_once( 'common/cleanstockprices.php' );
require_once( 'common/webpage2txt.php' );
require_once( 'common/yahooexchanges.php' );

//Define some constants
$const_YEAR = "1970";
$const_MONTH = "1";
$const_DAY = "01";

function getnewest( $flog, $thisex )
{
/*20090705 KF
*We will also have the case of this hasn't been run for
*a few days so the latest entries aren't here. We will
*need to do the opposite - find the latest and use that
*as the start dates.
*/
	fwrite( $flog, "\n\nSTARTING download of newest data\n" );
	cleanstockprices();
	$stockprices = new stockprices();
	$stockprices->querystring = "
	SELECT p.symbol as stocksymbol, max( p.date ) as date, 
	YEAR(max( p.date )) as year, MONTH(max( p.date )) as month, DAY(max( p.date )) as day, 
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
		fwrite( $flog, "If Symbol " . $symbol . ", Year " . $value['year'] . " Month " . $value['month'] . " less than or equal to " . date( 'Y' ) .  " " . date( 'm' ) . ".  Download!\n");
		$gonew = "no";
		if ( $symbol != 'CASH' )
		{
			if ($value['year'] < date( 'Y' ) )
			{
				$gonew = "yes";
			}
			else  
			if ($value['year'] = date( 'Y' ) )
			{
				if ($value['month'] < date( 'm' ) )
				{
						$gonew = "yes";
				}
				else 
				if ($value['month'] = date( 'm' ) )
				{
					if ($value['day'] < date( 'd' ) )
					{
						$gonew = "yes";
					}
					else
					{
						$gonew = "no";
					}
					
				}
				else
				{
					$gonew = "no";
				}
			}	
			else
			{
				$gonew = "no";
			}
		}
		if ($gonew == "yes")		
		{
			fwrite( $flog, "Downloading $symbol\n" );
			$filename = QueryYahoo( $symbol, $thisex[ $value['stockexchange'] ] 
						,$value['year'], date( 'Y' ),
						$value['month'] - 1, date( 'm' ),
						$value['day'] + 1, date( 'd' ),
						$flog
						);
			extractinsert( $flog, $filename, $symbol, $value );
		}
		cleanstockprices();
	}
	unset( $gonew );
	unset( $stockprices );
	return SUCCESS;
}
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
						$const_MONTH - 1, $value['month'] - 1, 
						$const_DAY, $value['day'] - 1,
						$flog
						);
			extractinsert( $flog, $filename, $symbol, $value );
		}
	}
	unset( $stockprices );
	return SUCCESS;
}

function getmissing( $flog, $thisex )
{
	/*20090705 KF
	*The following logic grabs all symbols not currently
	*in the stockprices database and then adds them
	*/
global $const_YEAR;
global $const_MONTH;
global $const_DAY;
	
	$stock = new stockinfo();
	$stock->where = "stocksymbol not in (select symbol from stockprices)";
	$stock->Select();
	foreach( $stock->resultarray as $key => $value )
	{
		$symbol = $value['stocksymbol'];
		$idstockinfo = $value['idstockinfo'];
		if( 
			( $symbol != 'CASH' )
			AND ( $symbol != 'BOO' )
			AND ( $symbol != 'ZZZ' )
		)
		{
			$filename = QueryYahoo( $symbol, $thisex[ $value['stockexchange'] ] 
						,$const_YEAR, date( 'Y' ), 
						$const_MONTH - 1, date( 'm' ), 
						$const_DAY, date( 'd' ),
						$flog
						);
			extractinsert( $flog, $filename, $symbol, $value );
		}
	}
	unset( $stock );
	return SUCCESS;
}


function extractinsert( $flog,  $filename = NULL, $symbol, $value )
{
	return;
	if( NULL == $filename )
	{
		fwrite( $flog, "No file to extract data from\n" );
		return FAILURE;
	}
	else
	if( NULL == $symbol )
	{
		fwrite( $flog, "No symbol to wrtie data for\n" );
		return FAILURE;
	}
	else
	if( NULL == $value )
	{
		fwrite( $flog, "No idstockinfo to write data for\n" );
		return FAILURE;
	}
	else
	{
		$fp = fopen( $filename, "r" );
		if( NULL == $fp )
		{
			fwrite( $flog, "Can't open data file $filename\n" );
			return FAILURE;
		}
		$stockprices = new stockprices();
		$tradedates = new tradedates();
		while( !feof( $fp ))
		{
			$fields = fgetcsv( $fp, 1024 );
			/* Yahoo CSV format:
			*Date,
			*Open,
			*High,
			*Low,
			*Close,
			*Volume,
			*Adj Close
			*/
			$insert['date'] = $fields[0];
			$insert['day_open'] = $fields[1]; 
			$insert['day_high'] = $fields[2]; 
			$insert['day_low'] = $fields[3]; 
			$insert['day_close'] = $fields[4]; 
			$insert['volume'] = $fields[5]; 
			$insert['adjustedclose'] = $fields[6]; 
			$insert['symbol'] = $symbol;
			$insert['idstockinfo'] = $value['idstockinfo'];
			if( $insert['date'] != NULL )
			{
				$stockprices->UpdateInsert( $insert );
				unset($stockprices->log);
				unset($stockprices->errors);
				$tradedates->Insert( $insert );
				unset($tradedates->log);
				unset($tradedates->errors);
			}
			unset( $insert );
			unset( $fields );
		}
		unset($stockprices);
		unset($tradedates);
		fclose( $fp );
		return SUCCESS;
	}
}




function QueryYahoo( $stock, $stockexchange = "" 
	,$STARTYEAR='2000', $ENDYEAR='2009', 
	$STARTMONTH='0', $ENDMONTH= '11', 
	$STARTDAY='01', $ENDDAY= '31',
	$flog = NULL
	)
{

//$query = "http://finance.yahoo.com/d/quotes.csv?s=CP.TO&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";
//$query = "http://finance.yahoo.com/d/quotes.csv?s=CNR.TO&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";
//http://ca.rd.yahoo.com/finance/quotes/internal/historical/download/*http://ichart.finance.yahoo.com/table.csv?s=CSCO&amp;a=2&amp;b=26&amp;d=5&amp;e=30&amp;f=2009&amp;g=d&amp;c=1990&amp;ignore=.csv
//20090926 http://ichart.finance.yahoo.com/table.csv?s=APF-UN.TO&amp;a=8&amp;b=26&amp;d=09&amp;e=26&amp;f=09
//20110926 Discoverd that ichart.finance.yahoo.com gives a 404 error.  
//	finance.yahoo.com above still works for a daily quote.
//	Using their site for CP we were able to construct
//	http://ichart.finance.yahoo.com/table.csv?s=CP&d=8&e=27&f=2011&g=d&a=11&b=30&c=1983&ignore=.csv
//	where
//		d = to month
//		e = to day
//		f = to year
//		a = from month
//		b = from day
//		c = from year
//		g = type (daily, weekly, etc)
	$SERVERURL = "http://ichart.finance.yahoo.com/table.csv?";
	$SYMBOLIND = "s=";
	$STARTMONTHIND = "&a=";
	$STARTDAYIND = "&b=";
	$STARTYEARIND = "&c=";
	$ENDMONTHIND = "&d=";
	$ENDDAYIND = "&e=";
	$ENDYEARIND = "&f=";
	$IGNOREIND = "&ignore=.csv";
	$INTERVALIND = "&g=d";	

	if( $STARTYEAR == $ENDYEAR and $STARTMONTH == $ENDMONTH and $STARTDAY == $ENDDAY )
	{
		fwrite( $flog, "Stock $stock has reached the end of the date limits\n" );
		return NULL;
	}
	if( strlen($stockexchange) > 0) 
	{
		$symbol = $stock . "." . $stockexchange;
	}
	else
	{
		$symbol = $stock;
	}
	//The following can all be set to change the parameters
	//$query = "http://ichart.finance.yahoo.com/table.csv?s=" . $symbol . "&a=" . $STARTMONTH . "&b=" . $STARTDAY . "&d=" . $ENDMONTH . "&e=" . $ENDDAY . "&f=" . $ENDYEAR . "&g=d&c=" . $STARTYEAR . "&ignore=.csv";
	$query = $SERVERURL . $SYMBOLIND . $symbol . $STARTMONTHIND . $STARTMONTH . $STARTDAYIND . $STARTDAY . $ENDMONTHIND . $ENDMONTH . $ENDDAYIND . $ENDDAY . $ENDYEARIND . $ENDYEAR . $INTERVALIND . $IGNOREIND;
echo $query . "\n";
	fwrite( $flog, "URL:  $query\n" );
	$text = webpage2txt( $query );
	$filename = "../currentdata/" . $symbol . "." . $STARTYEAR . $STARTMONTH . $STARTDAY . "-" . $ENDYEAR . $ENDMONTH . $ENDDAY .  ".csv";
	fwrite( $flog, "Data file:  $filename\n\n" );
	$fp = fopen( $filename, "w" );
	if( NULL == $fp )
	{
		fwrite( $flog, "couldn't create $filename\n" );
		$filename = NULL;
	}
	else
	{
		fwrite( $fp, $text );
		fclose ( $fp );
		$len = strlen( $text );
		fwrite( $flog, "Wrote " . $len . " characters\n" );
		if( $len == 0 )
			$filename = NULL;
	}
	unset( $text );
	return $filename;
}

/*
$page = new genericpage();
$page->mode = "search";
$menu = $Security->AddMenu();
$page->SetItem( $menu );
*/

/*20090801 KF
* Add a logfile to the prog
*/
$flog = fopen( "../logs/queryyahoo-historical" . date( 'Ymdhs' ) . ".txt", "w" );
fwrite( $flog, "Started run" );

$_getmissing = 1;
$_getoldest = 1;
//$tradedates = new tradedates();
//$stockprices = new stockprices();
//$stock = new stockinfo();
$stockexchange = new stockexchange();

/*
*$stockexchange->Select();
*foreach( $stockexchange->resultarray as $key => $evalue )
*{
*	$thisex[ $evalue['idstockexchange'] ] = $evalue['YahooSymbol'];
*}
*//var_dump( $thisex );
*unset( $stockexchange );
*/

$thisex = yahooexchanges();

getnewest( $flog, $thisex );
if( isset( $_getmissing ))
{
	getmissing( $flog, $thisex );
}
if( isset( $_getoldest))
{
	getoldest( $flog, $thisex );
}
fclose( $flog );
?>

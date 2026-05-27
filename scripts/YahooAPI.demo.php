<?php

//require_once(dirname(__FILE__) . '/YahooFinanceAPI.php');
require_once('data/YahooFinanceAPI/YahooFinanceAPI.php');
spl_autoload_register(array('YahooFinanceAPI', 'autoload'));
require_once("YahooCreateAPI.php");
require_once("YahooAdd2Tables.php");


/************************************************************************************
	Get the list of stocks to look up
	They need to be Active, and not CASH
************************************************************************************/
require_once( '../local.php' );
require_once( 'data/generictable.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
include( $MODELDIR . '/stockinfo.class.php' );
include( $MODELDIR . '/stockprices.class.php' );
include( $MODELDIR . '/stockexchange.class.php' );
include( $MODELDIR . '/technicalanalysis.class.php' );
$stock = new stockinfo();

/*
* $stock->querystring = "count(*) from stockinfo where active='1'";
*$stock->where = "active='1'";
*$stock->orderby = "";
*$stock->select = "select count(*) as count";
*$stock->Select();
*var_dump( $stock->resultsarray );
*echo $stock->resultsarray[0]["count"] . "Stocks returned as active \n";
*exit;
*/

$stock->where = "active='1'";
//$stock->limit = 199; //Yahoo limits to 200 or less at a time
$stock->Select();
$yahoototalcount = 0;
$yahooquerycount = 0;
$good = 0;
$stockscount = $stock->resultrows;
$api = createAPI();
foreach( $stock->resultarray as $key => $value )
{
	/************************************************************************************
		Will need to repeat for stocks above 199...
	************************************************************************************/
	if( $yahooquerycount > 198 )
	{
		$good += getResults( $api );

		$yahoototalcount += $yahooquerycount;
		unset( $api );
		$api = createAPI();
		$yahooquerycount = 0;
	}
	$symbol = $value['stocksymbol'];
      	if ( $symbol != 'CASH' )
        {
		$api->addSymbol( $symbol );
		$yahooquerycount++;
	}
}
/************************************************************************************
	Odds are we will not see a multiple of 199
	so we need to run the getResults one last time
************************************************************************************/
	$good += getResults( $api );
	$yahoototalcount += $yahooquerycount;
	unset( $api );

echo "Sought resutls for " . $yahoototalcount . " stocks with " . $good . " inserts attempted \n";

exit();

/************************************************************************************************************************
************************************************************************************************************************
************************************************************************************************************************
				Called Functions
************************************************************************************************************************
************************************************************************************************************************
************************************************************************************************************************/

function getResults( $api )
{
	$success=0;
	$stockexchange = new stockexchange();
	$stockinfo = new stockinfo();
	$technicalanalysis = new technicalanalysis();
	$result = $api->getQuotes();
	if( $result->isSuccess() ) 
	{
	    	$quotes = $result->data;
	    	foreach( $quotes as $quote ) 
		{
			//var_dump( $quote );
			/************************************************************************************
			*	Find the correct stockinfo row since 
			*	symbols are unique only within an exchange
			************************************************************************************/
			foreach( $stockinfo->fieldlist as $col )
			{
				$stockinfo->$col = NULL;
			}
			$stockinfo->stocksymbol = $quote->symbol;
			foreach( $stockexchange->fieldlist as $col )
			{
				$stockexchange->$col = NULL;
			}
			$stockexchange->YahooExchangeName = $quote->stockExchange;
			$stockexchange->fieldspec['YahooExchangeName']['prikey'] = 'Y';
			$res = $stockexchange->GetVARRow();
			if( TRUE == $res)
			{
				//We have a result
				$stockinfo->idstockexchange = $stockexchange->idstockexchange;
				/************************************************************************************
				*	Process the results adding them to the tables
				************************************************************************************/
				$sres = $stockinfo->GetVARRow();
				if( TRUE == $sres )
				{
					updateStockinfo( $quote, $stockinfo );
				}
				else
				{
					addStockinfo( $quote, $stockinfo );
				}
				addStockprices( $quote, $stockinfo );
				addTechnicalanalysis( $quote, $stockinfo );
				$success++;
			}
			else
			{
				echo "No results found for stock exchange " . $stockexchange->YahooExchangeName . "\n";
			}
	    	}
	}
	return $success;
}

	

?>

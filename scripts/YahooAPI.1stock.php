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


function getStockExchangeYahoo( $idstockexchange )
{	
	$stockexchange = new stockexchange();
	$stockexchange->idstockexchange = $idstockexchange;
	$stockexchange->GetVARRow();
	return $stockexchange->YahooSymbol;
}	
function getIDStockExchange( $symbol )
{	
	$stockexchange = new stockexchange();
	$stockexchange->where = "googlesymbol = '" . $symbol . "' or YahooSymbol = '" . $symbol . "'";
	$stockexchange->Select();
	if( isset( $stockexchange->resultsarray[0] ))
	{
		$idstockexchange = $stockexchange->resultsarray[0]['idstockexchange'];
	}
	else
	{
		//Assumption that if we don't have the symbol set we are talking Cdn stock on TSE
		$idstockexchange = 1;
	}
	return $idstockexchange;
}	


$idstockexchange = getIDStockExchange( $argv[2] );
$stock->where = "stocksymbol = '" . $argv[1] . "' and idstockexchage = '" . $idstockexchange . "'";
$stock->Select();
$yahoosymbol = $stock->stocksymbol . "." . getStockExchangeYahoo( $idstockexchange );

$yahoototalcount = 0;
$yahooquerycount = 0;
$good = 0;
$stockscount = $stock->resultrows;
$api = createAPI();
$symbol = $argv[1];
$exchange = $argv[2];

$api->addSymbol( $yahoosymbol );
$yahooquerycount++;
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
				*	Need to trim the exchange off of the symbol in quote for this to work properly
				************************************************************************************/
				$yahooexchange = getStockExchangeYahoo( $stockexchange->idstockexchange );

				/************************************************************************************
				*	Process the results adding them to the tables
				************************************************************************************/
				$sres = $stockinfo->GetVARRow();
				if( TRUE == $sres )
				{
					updateStockinfo( $quote, $stockinfo );
					echo "Ran UpdateStockinfo\n";
					//var_dump( $stockinfo );
					var_dump( $quote );
				}
				else
				{
					addStockinfo( $quote, $stockinfo );
					echo "Ran AddStockinfo\n";
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

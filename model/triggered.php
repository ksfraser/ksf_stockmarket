<?php
//20081227 Eventum Framework Issue 35
//Due to auto gen of Pre/Post action triggers, having
//the same column in multiple tables can lead to trigger loops
//when the update in 1 table cascades to the others.

function PostperatioUpdate( $data )
{
	if( $data['callingclass'] != "stockinfo" )
	{
		//Trigger loops.  Many tables using FK use the same column name which
		//when they get inserted, call this fcn name
		return NULL;
	}
	//Tell ratios about the peratio
	require_once( 'ratios.class.php' );
	$ratios = new ratios();
	$ratios->Update( $data );
	return SUCCESS;
}

function PostidratiosInsert( $data )
{
	if( $data['callingclass'] != "ratios" )
	{
		//Trigger loops.  Many tables using FK use the same column name which
		//when they get inserted, call this fcn name
		return NULL;
	}
}


/*********************************************************************************************************************
*
*	20111215 KF moved into codemeta_functions as part of stockinfo_PoststocksymbolInsert
*
function PostidstockinfoInsert( $data )
{
	//20090607 KF Eventum 136
	//when a stock is inserted, also download the financial statement
//	echo "triggered::PostidstockinfoInsert <br /><br />\n";
	if( isset( $data['stockinfo']['loop'] ))
	{
		//Looping due to triggered inserts
	//	 echo "triggered::PostidstockinfoInsert looping so exit <br /><br />\n";
		return NULL;
	}
	else
	{
		$data['stockinfo']['loop'] = 1;
	}
	if( $data['callingclass'] != "stockinfo" )
	{
		//Trigger loops.  Many tables using FK use the same column name which
		//when they get inserted, call this fcn name
		return NULL;
	}
	$data['idstockinfo'] = $data['lastinsertid'];
 	require_once( '../scripts/getbondratearray.php' );
        $bondratearray = getbondratearray( "10" );
	require_once( 'stockexchange.class.php' );
//$stockinfo->querystring = "Select s.stocksymbol, e.googlesymbol, s.idstockinfo, s.currentprice from stockinfo s, stockexchange e where s.stockexchange = e.idstockexchange order by s.idstockinfo desc";
//$stockinfo->GenericQuery();
	$exchange = new stockexchange();
	$exchange->where = "idstockexchange = '" . $data['stockexchange'] . "'";
	$exchange->Select();
//	var_dump( $exchange->querystring );
//	echo "<br />Exchange:<br />\n";
//	var_dump( $exchange );
//	echo "<br />Exchange Resultarray:<br />\n";
//	var_dump( $exchange->resultarray );
	$data['googlesymbol'] = $exchange->resultarray[0]['googlesymbol'];
	echo "<br />triggered::PostidstockinfoInsert Data:<br />\n";
	//var_dump( $data );
//	echo "<br />triggered::PostidstockinfoInsert Calling getstockfinancial<br />\n";

	require_once( '../scripts/financialstatements/getstockfinancials.php' );
	//data has to contain stocksymbol, googlesymbol and idstockinfo
        getstockfinancial( $data, $bondratearray );
	return;
	//!#136

}
*******************************************************************************/

function inserttenants( $data )
{
//	//var_dump( $data );
	//echo "triggered.php::inserttenants\n";
	include_once( 'tenets.class.php' );
	$t = new tenets();
	$insert['symbol'] = $data;
	$t->Insert( $insert );
	return;
}

function si_postannualdividendpershareupdate( $data )
{
//This is designed to be called from stockinfo,
//calling from portfolio will result in a trigger loop!!
//var_dump( $data );
//	debug_print_backtrace();
//	return;
	//echo "triggered.php::postannualdividedpershareupdate\n";
	if( isset( $data['stocksymbol'] ) )
	{
		require_once( 'portfolio.class.php' );
		$portfolio = new portfolio();
		$update['annualdividendpershare'] = $data['annualdividendpershare'];
//		$portfolio->where = "stocksymbol = '" . $data['stocksymbol'] . "'";
//Setting the following so that the "WHERE" gets set, and passed onto triggered fcn's
		$update['stocksymbol'] = $data['stocksymbol'];
		$oldspec = $portfolio->fieldspec['stocksymbol']['prikey'];
		$portfolio->fieldspec['stocksymbol']['prikey'] = "Y";
		$portfolio->Update( $update );
//Return to old value
		$portfolio->fieldspec['stocksymbol']['prikey'] = $oldspec;
	}
	//echo "end triggered.php::postannualdividedpershareupdate\n";
	return;
}

function postcurrentpriceupdate( $data )
{
//	//var_dump( $data );
	//Eventum project finance issue #32
	//undefined index stocksymol below.  Since this proc depends on the symbol
	//check and exit if it doesn't exist.
	if( !isset( $data['stocksymbol'] ))
		return;
	//!#32
	//echo "triggered.php::postcurrentpriceupdate\n";
	require_once( 'portfolio.class.php' );
	$portfolio = new portfolio();
	$portfolio->querystring = "update portfolio set currentprice='" . $data['currentprice'] . "' where stocksymbol = '" . $data['stocksymbol'] . "'";
	$portfolio->GenericQuery();
	return;
}

function transactionupdateportfolio( $data )
{
//Want to update the portfolio data for
//transactions (stock totals)
	//echo "triggered.php::transactionupdateportfolio";
	require_once( 'portfolio.class.php' );
	$portfolio = new portfolio();
	$select['username'] = $_POST['username'];
	$select['symbol'] = $_POST['stocksymbol'];
	$numbershares = CalculateNumberShares( $_POST['username'], $_POST['stocksymbol'] );
	//////echo "NS: $numbershares<br />";
	$bookvalue = Calculatebookvalue( $_POST['username'], $_POST['stocksymbol'] );
	//////echo "BV: $bookvalue<br />";
	$portfolio->where = "username='" . $_POST['username'] . "' and stocksymbol = '" . $_POST['stocksymbol'] . "'";
	$portfolio->Select();
	////var_dump( $portfolio->resultarray );
	//If we have a idportfolio, then there is an entry to update, else insert
	if ( isset( $portfolio->resultarray[0]['idportfolio'] ) )
	{
		//////echo "<br />Is set idportfolio: " .  $portfolio->resultarray[0]['idportfolio'] . "<br />";
		$update['bookvalue'] = $bookvalue;
		$update['numbershares'] = $numbershares;
		$update['idportfolio'] = $portfolio->resultarray[0]['idportfolio'];
		$portfolio->Update( $update );
		//////echo "<br />Query was " . $portfolio->querystring . "<br />";
	}
	else
	{
		$insert['stocksymbol'] = $_POST['stocksymbol'];
		$insert['username'] = $_POST['username'];
		$insert['bookvalue'] = $bookvalue;
		$insert['numbershares'] = $numbershares;
		$portfolio->Insert( $insert );
		////var_dump( $portfolio->errors );
		//////echo "<br />Query was " . $portfolio->querystring . "<br />";
	}
	return;
}

function updateportfolio( $data )
{
//Want to update the portfolio data for
//either updated stockinfo (Current price)
	//echo "triggered.php::updateportfolio";
	////var_dump( $data );
	require_once( 'portfolio.class.php' );
	$portfolio = new portfolio();
	if( isset( $_POST['transactiontype'] ) )
	{
		$transaction = ltrim( rtrim( $_POST['transactiontype'] ));
		//Was a transaction activity, check for
		//portfolio already having the stock
		$select['username'] = $_POST['username'];
		$select['symbol'] = $_POST['stocksymbol'];
		$numbershares = CalculateNumberShares( $_POST['username'], $_POST['stocksymbol'] );
		$bookvalue = Calculatebookvalue( $_POST['username'], $_POST['stocksymbol'] );

		$portfolio->where = "username='" . $_POST['username'] . "' and stocksymbol = '" . $_POST['stocksymbol'] . "'";
		$portfolio->Select();
/*
			//Don't already have the stock in the portfolio
			$insert['symbol'] = $_POST['stocksymbol'];
			$insert['username'] = $_POST['username'];
			$insert['bookvalue'] = $_POST['dollar'];
			if( strcasecmp( $transaction, "BUY" ) == 0 )
			{
				$insert['numbershares'] = $_POST['numbershares'];
			}
			else
			if( strcasecmp( $transaction, "SELL" ) == 0 )
			{
				$insert['numbershares'] = 0 - $_POST['numbershares'];
			}
			else
			if( strcasecmp( $transaction, "SPLIT" ) == 0 )
			{
				//Can't split shares you don't own
			}
			$portfolio->Insert( $insert );
*/
	}
	return;
}

function PostNumberSharesUpdate( $data )
{
	//echo "triggered.php::PostNumberSharesUpdate";
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
	$portfolio->Select();
	//var_dump( $portfolio->resultarray );
	//////echo "<br />";
	$username = $portfolio->resultarray[0]['username'];
	$stocksymbol = $portfolio->resultarray[0]['stocksymbol'];
	$numbershares = $portfolio->resultarray[0]['numbershares'];
	$currentprice = $portfolio->resultarray[0]['currentprice'];
	$bookvalue = Calculatebookvalue( $username, $stocksymbol );
	$marketvalue = Calculatemarketvalue( $numbershares, $currentprice );
	$PL = Calculateprofitloss( $bookvalue, $marketvalue );
	$yield = CalculateYield( $bookvalue, $marketvalue );
	////echo "<br />Values NS: $numbershares CP: $currentprice <br />BV: $bookvalue MV: $marketvalue <br />PL: $PL Yield: $yield<br />";

	$update['idportfolio'] = $data['idportfolio'];
	$update['bookvalue'] = $bookvalue;
	$update['marketvalue'] = $marketvalue;
	$update['profitloss'] = $PL;
	$update['yield'] = $yield;
	$update['marketbook'] = $yield;
	//var_dump( $update );
	$portfolio->Update( $update );
	////echo "<br />Errors: ";
	//var_dump( $portfolio->errors );
	////echo "<br />Query was: $portfolio->querystring <br />";
	return;
}

function Calculatemarketbook( $market, $book )
{
	//echo "triggered.php::Calculatemarketbook";
	if( $book <> 0 )
		return $market / $book;
	else
		return 0;
}
function CalculateYield( $book, $market )
{
	//echo "triggered.php::CalculateYield";
	if( $book <> 0 )
		$percent = $market / $book;
	else 
		$percent = 0;
	return $percent;
}

function Calculateprofitloss( $book, $market )
{
	//echo "triggered.php::Calculateprofitloss";
	$profit = $market - $book;
	return $profit;
}

function Calculatemarketvalue( $numbershares, $currentprice )
{
	//echo "triggered.php::Calculatemarketvalue";
	return $numbershares * $currentprice;
}
	

function CalculateNumberShares( $username, $symbol )
{
//Update the book value of the share for the user
//This will be a sum of the transactions for the
//given stock for the given user
	//echo "triggered.php::CalculateNumberShares";

	$numbershares = 0;

include_once( 'transaction.class.php' );
	$transaction = new transaction();
	$transaction->select = "sum(numbershares) as buy";
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%BUY%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );
	////echo "<br />";
	$numbershares = $numbershares + $transaction->resultarray[0]['buy'];

	$transaction->select = "sum(numbershares) as drip";
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%DIV%REINV%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );
	////echo "<br />";
	$numbershares = $numbershares + $transaction->resultarray[0]['drip'];

	$transaction->select = "sum(numbershares) as split";
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%SPLIT%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );
	////echo "<br />";
	$numbershares = $numbershares + $transaction->resultarray[0]['split'];

	$transaction->select = "sum(numbershares) as sell";
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%SELL%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );

	$numbershares = $numbershares - $transaction->resultarray[0]['sell'];

	return $numbershares;
}

function Calculatedividendbookvalue( $username, $symbol )
{
//Update the book value of the share for the username
//This will be a sum of the transactions for the
//given stock for the given username
	//echo "triggered.php::Calculatedividendbookvalue";

	$dividendbookvalue = 0;

include_once( 'transaction.class.php' );
	$transaction = new transaction();
	$transaction->select = "sum(dollar) as dividend";
//Grab all DIVIDENDS and SPECIAL DIVIDENDS but ignore DIVFIDEND REINVESTMENT
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%DIVIDEND' and numbershares <> 0";
	$transaction->Select();
	//var_dump( $transaction->resultarray );
	////echo "<br />";

	$dividendbookvalue = $dividendbookvalue + $transaction->resultarray[0]['dividend'];
	////echo $username . "'s DividendBook for $symbol: $dividendbookvalue<br />\n";
	return $dividendbookvalue;
}

function Calculatebookvalue( $username, $symbol )
{
//Update the book value of the share for the username
//This will be a sum of the transactions for the
//given stock for the given username
	//echo "triggered.php::Calculatebookvalue";

	$bookvalue = 0;

include_once( 'transaction.class.php' );
	$transaction = new transaction();
	$transaction->select = "sum(dollar) as buy";
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%BUY%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );
	////echo "<br />";

	$bookvalue = $bookvalue + $transaction->resultarray[0]['buy'];
	$transaction->select = "sum(dollar) as sell";
	$transaction->where = "stocksymbol = '" . $symbol . "' and username = '" . $username . "' and transactiontype like '%SELL%'";
	$transaction->Select();
	////var_dump( $transaction->resultarray );

	$bookvalue = $bookvalue - $transaction->resultarray[0]['sell'];

	return $bookvalue;
}

function old_Calculatebookvalue( $data )
{
//Update the book value of the share for the username
//This will be a sum of the transactions for the
//given stock for the given username

////var_dump( $data );
	//echo "triggered.php::old_Calculatebookvalue";
include_once( 'portfolio.class.php' );
	$bookvalue = 0;
	$shares = 0;
	$idportfolio = $data['idportfolio'];
	$portfolio = new portfolio;
	$portfolio->select = "username, stocksymbol";
	$portfolio->where = "idportfolio = '" . $idportfolio . "'";
	$portfolio->Select();
	//var_dump( $portfolio->resultarray );
	////echo "<br />";

include_once( 'transaction.class.php' );
	$transaction = new transaction();
	//$transaction->select = "sum(dollar) as buy, sum(numbershares) as bought";
	$transaction->select = "sum(dollar) as buy";
	$transaction->where = "stocksymbol = '" . $portfolio->resultarray[0]['symbol'] . "' and username = '" . $portfolio->resultarray[0]['usernamename'] . "' and transactiontype like '%BUY%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );
	////echo "<br />";

	$bookvalue = $bookvalue + $transaction->resultarray[0]['buy'];
	//$shares = $shares + $transaction->resultarray[0]['buy'];
	//$transaction->select = "sum(dollar) as sell, sum(numbershares) as sold";
	$transaction->select = "sum(dollar) as sell";
	$transaction->where = "stocksymbol = '" . $portfolio->resultarray[0]['symbol'] . "' and username = '" . $portfolio->resultarray[0]['usernamename'] . "' and transactiontype like '%SELL%'";
	$transaction->Select();
	//var_dump( $transaction->resultarray );

	$bookvalue = $bookvalue - $transaction->resultarray[0]['sell'];
	//$shares = $shares - $transaction->resultarray[0]['sold'];
	$update['idportfolio'] = $idportfolio;
	$update['bookvalue'] = $bookvalue;
	//Don't want to get into an endless recursive loop.  
	//UpdatePortfolio updates the number of shares
	//$update['numbershares'] = $shares;
	$portfolio->Update( $update );

	return;
}

function Calculatedividendpercentbookvalue( $data )
{
	//The percent of the bookvalue that this share's BV is
	//var_dump( $data );
	//echo "triggered.php::Calculatedividendpercentbookvalue";
include_once( 'portfolio.class.php' );
	//$username = $data['username'];
	$idportfolio = $data['idportfolio'];
	$stocksymbol = $data['stocksymbol'];
	$bookvalue = $data['bookvalue'];
	$numbershares = $data['numbershares'];
	$portfolio = new portfolio;
	$portfolio->noExtraSQL = 1;
	$portfolio->where = "idportfolio = '" . $idportfolio . "'";
	$portfolio->Select();
	$username = $portfolio->resultarray[0]['username'];
	//Do we need to grab the book value, or is it passed snce it was part of the update
	////echo "CPBV: $bookvalue<br />";
	//$portfolio->where = "stocksymbol = '" . $stocksymbol . "' and username = '" . $username . "'";
	$portfolio->select = "sum(bookvalue) as portfoliobv";
	$portfolio->where = "username = '" . $username . "' and numbershares <> 0";
	$portfolio->Select();
	$portfoliobv = $portfolio->resultarray[0]['portfoliobv'];
	return $bookvalue/$portfoliobv;
}

function Calculatedividendpercentmarketvalue( $data )
{
	//The percent of the marketvalue that this share's MV is
	//var_dump( $data );
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->noExtraSQL = 1;
	//Do we need to grab the market value, or is it passed snce it was part of the update
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
	$portfolio->Select();
	$marketvalue = $portfolio->resultarray[0]['marketvalue'];
	//$portfolio->where = "stocksymbol = '" . $stocksymbol . "' and username = '" . $username . "'";
	$username = $portfolio->resultarray[0]['username'];
	$portfolio->select = "sum(marketvalue) as portfoliomv";
	$portfolio->where = "username = '" . $username . "' and numbershares <> 0";
	$portfolio->Select();
	$portfoliomv = $portfolio->resultarray[0]['portfoliomv'];
	return $marketvalue/$portfoliomv;
}

function CalculatePercentDividend( $data )
{
	//The percent of the dividend that this share's Div is
	//var_dump( $data );
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->noExtraSQL = 1;
	//Do we need to grab the market value, or is it passed snce it was part of the update
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
	$portfolio->Select();
	$dividend = $portfolio->resultarray[0]['annualdividendpershare'];
	//$portfolio->where = "stocksymbol = '" . $stocksymbol . "' and username = '" . $username . "'";
	$username = $portfolio->resultarray[0]['username'];
	$portfolio->select = "sum(annualdividendpershare) as portfoliodividend";
	$portfolio->where = "username = '" . $username . "' and numbershares <> 0";
	$portfolio->Select();
	$portfoliodividend = $portfolio->resultarray[0]['portfoliodividend'];
	return $dividend/$portfoliodividend;
}

function Calculatepercenttotalmarketvalue( $data )
{
	//The percent of the marketvalue that this share's Div is
	//var_dump( $data );
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->noExtraSQL = 1;
	//Do we need to grab the market value, or is it passed snce it was part of the update
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
	$portfolio->Select();
	$marketvalue = $portfolio->resultarray[0]['marketvalue'];
	//$portfolio->where = "stocksymbol = '" . $stocksymbol . "' and username = '" . $username . "'";
	$username = $portfolio->resultarray[0]['username'];
	$portfolio->select = "sum(marketvalue) as portfoliomarketvalue";
	$portfolio->where = "username = '" . $username . "' and numbershares <> 0";
	$portfolio->Select();
	$portfoliomarketvalue = $portfolio->resultarray[0]['portfoliomarketvalue'];
	return $marketvalue/$portfoliomarketvalue;
}

function Calculatepercenttotaldividend( $data )
{
	//The percent of the dividend that this share's Div is
	//var_dump( $data );
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->noExtraSQL = 1;
	//Do we need to grab the market value, or is it passed snce it was part of the update
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
	$portfolio->Select();
	$dividend = $portfolio->resultarray[0]['annualdividendpershare'];
	//$portfolio->where = "stocksymbol = '" . $stocksymbol . "' and username = '" . $username . "'";
	$username = $portfolio->resultarray[0]['username'];
	$portfolio->select = "sum(annualdividendpershare) as portfoliodividend";
	$portfolio->where = "username = '" . $username . "' and numbershares <> 0";
	$portfolio->Select();
	$portfoliodividend = $portfolio->resultarray[0]['portfoliodividend'];
	return $dividend/$portfoliodividend;
}

function Calculatepercenttotalbookvalue( $data )
{
	//The percent of the bookvalue that this share's Div is
	//var_dump( $data );
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->noExtraSQL = 1;
	//Do we need to grab the market value, or is it passed snce it was part of the update
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "' and numbershares <> 0";
	$portfolio->Select();
	$bookvalue = $portfolio->resultarray[0]['bookvalue'];
	//$portfolio->where = "stocksymbol = '" . $stocksymbol . "' and username = '" . $username . "'";
	$username = $portfolio->resultarray[0]['username'];
	$portfolio->select = "sum(bookvalue) as portfoliobookvalue";
	$portfolio->where = "username = '" . $username . "' and numbershares <> 0";
	$portfolio->Select();
	$portfoliobookvalue = $portfolio->resultarray[0]['portfoliobookvalue'];
	return $bookvalue/$portfoliobookvalue;
}

function Calculatedividendyield( $data )
{
	return $data['annualdividendpershare'] / $data['currentprice'];
}

function postportfoliodividendupdate( $data )
{
	//If the corporate annual dividend is updated, it will change:
	//	Dividend Percent of Book Value
	//	Dividend Percent of Market Value
	//	Dividend Yield
	//	Dividend % of portfolio dividend yield
	////echo "PPDU<br />\n";
	//var_dump( $data );
	//As long as the query was properly set up, we will have the stocksymbol
	//that was changed so we can find out what rows to fix
	require_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->where = "stocksymbol = '" . $data['stocksymbol'] . "'";
	////echo "<br />$portfolio->where<br />";
	$portfolio->noExtraSQL = 1;
	$portfolio->Select();
	////echo "PPDU Post Select<br />\n";
	//var_dump( $portfolio->resultarray[0] );
	////echo "<br />\n";
	foreach( $portfolio->resultarray as $data2 )	
	{
		//var_dump( $data2 );
		////echo "<br />\n";
		$dppd = CalculatePercentDividend( $data2 );
		$ptd = Calculatepercenttotaldividend( $data2 );
		$ptbv = Calculatepercenttotalbookvalue( $data2 );
		$ptmv = Calculatepercenttotalmarketvalue( $data2 );
		$dpbv = Calculatedividendpercentbookvalue( $data2 );
		$dpmv = Calculatedividendpercentmarketvalue( $data2 );
		$dy = Calculatedividendyield( $data2 );
		$update['percenttotaldividend'] = $ptd;
		$update['percenttotalmarketvalue'] = $ptmv;
		$update['percenttotalbookvalue'] = $ptbv;
		$update['dividendpercentbookvalue'] = $dpbv;
		$update['dividendpercentmarketvalue'] = $dpmv;
		$update['dividendyield'] = $dy;
		$update['idportfolio'] = $data2['idportfolio'];
		//var_dump( $update );
		////echo "<br />\n";
		//$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
		$portfolio->Update( $update );
	}
/*
include_once( 'portfolio.class.php' );
	$portfolio = new portfolio;
	$portfolio->where = "idportfolio = '" . $data['idportfolio'] . "'";
	$portfolio->Update( $update );
*/
	return;
}

/* 
function UpdateStockinfoDividend( $data = NULL )
{
	//echo "triggered.php::UpdateStockinfoDividend";
        if ($data != NULL)
        {
                //Send the dividend value to the stockinfo table for this stock
                require_once( 'stockinfo.class.php' );
                $s = new stockinfo();
                //var_dump( $data );
                $update['idstockinfo'] = $data['idstockinfo'];
                $update['annualdividendpershare'] = $data['dividendpershare'];
                $s->Update( $update );
        }
}
*/

?>

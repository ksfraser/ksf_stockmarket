<?php

//20090804 KF
//Account transactions:
//	Add cash
//	Remove cash
//	Convert currencies
//	Buy Stocks
//	Sell Stocks
//	Dividends
//	Dividend re-investment
//	Exchange
//	Split
//	Reverse Split
//	Merger
//	Takeover
//	Transfer
//	Currency Exchange Buy
//	Currency Exchange sell
//	Special Dividend

//addtransaction( $flog, $username, $symbol, $numbershares, $dollar, $action, $transactiondate, $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )

require_once( 'addtransaction.php' );

function cleanuser( $flog, $user )
{
	fwrite( $flog, "Cleaning up old transactions for the user $user\n" );
	require_once( '../model/transaction.class.php' );
	$transaction = new transaction();
	$transaction->querystring = "DELETE from transaction where username = '" . $user . "'";
	$transaction->GenericQuery();
}

function addcash( $flog, $user, $dollars, $transactiondate, $currency = "CAD", $account = "TRADE" )
{
	fwrite( $flog, "Adding $" . $dollars . " to the portfolio\n" );
	return addtransaction( $flog, $user, "CASH", $dollars, $dollars, "TRANSFERIN", $transactiondate, $currency, $currency, $account );
}

function removecash( $flog, $user, $dollars, $transactiondate, $currency = "CAD", $account = "TRADE" )
{
	fwrite( $flog, "Removing $" . $dollars . " to the portfolio\n" );
	return addtransaction( $flog, $user, "CASH", $dollars, $dollars, "TRANSFEROUT", $transactiondate, $currency, $currency, $account );
}

function convertcash( $flog, $user, $fromdollars, $todollars, $transactiondate, $fromcurrency = "CAD", $tocurrency = "USD", $account = "TRADE" )
{
	fwrite( $flog, "Converting cash from " . $fromdollars . " to " . $todollars . "\n" );
	addtransaction( $flog, $user, "CASH", $fromdollars, $fromdollars, "SELL", $transactiondate, $fromcurrency, $fromcurrency, $account );
	addtransaction( $flog, $user, "CASH", $todollars, $todollars, "BUY", $transactiondate, $tocurrency, $tocurrency, $account );
	return SUCCESS;
}

function buystock ( $flog, $username, $symbol, $numbershares, $dollar, $transactiondate, $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )
{
	fwrite( $flog, "Buying " . $numbershares . " of stock " . $symbol . " for $" . $dollar . "\n" );
	addtransaction( $flog, $username, $symbol, $numbershares, $dollar, "BUY",  $transactiondate, $currency, $foreigncurrency, $account );
	addtransaction( $flog, $username, "CASH",  $dollar,       $dollar, "SELL", $transactiondate, $currency, $foreigncurrency, $account );
}

function sellstock ( $flog, $username, $symbol, $numbershares, $dollar, $transactiondate, $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )
{
	fwrite( $flog, "Selling " . $numbershares . " of stock " . $symbol . " for $" . $dollar . "\n" );
	addtransaction( $flog, $username, $symbol, $numbershares, $dollar, "SELL", $transactiondate, $currency, $foreigncurrency, $account );
	addtransaction( $flog, $username, "CASH",  $dollar,       $dollar, "BUY",  $transactiondate, $currency, $foreigncurrency, $account );
}

function dividend( $flog, $username, $symbol, $numbershares, $dollar, $transactiondate, $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )
{
	fwrite( $flog, "Received dividend for " . $symbol . " of $" . $dollar . "\n" );
	addtransaction( $flog, $username, $symbol, "0",     $dollar, "DIVIDEND", $transactiondate, $currency, $foreigncurrency, $account );
	addtransaction( $flog, $username, "CASH",  "0",     $dollar, "BUY",      $transactiondate, $currency, $foreigncurrency, $account );
}

function dividendreinvest( $flog, $username, $symbol, $numbershares, $dollar, $transactiondate, $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )
{
	fwrite( $flog, "Received dividend for " . $symbol . ".  Reinvested as " . $numbershares . " shares\n" );
	addtransaction( $flog, $username, $symbol, $numbershares, "0", "DIVIDEND REINVESTMENT", $transactiondate, $currency, $foreigncurrency, $account );
}

function CalculateDollarsAvailable( $username )
{
        $dollar = 0;
	require_once( '../model/transaction.class.php' );
        $transaction = new transaction();
	$transaction->fieldspec['username']['extra_sql'] = "";
	$transaction->orderby = "";

        $transaction->select = "sum(dollar) as buy";
        $transaction->where = "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%BUY%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $dollar = $dollar + $transaction->resultarray[0]['buy'];

        $transaction->select = "sum(dollar) as drip";
        $transaction->where = "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%DIV%REINV%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $dollar = $dollar + $transaction->resultarray[0]['drip'];

        $transaction->select = "sum(dollar) as split";
        $transaction->where = "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%SPLIT%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $dollar = $dollar + $transaction->resultarray[0]['split'];

        $transaction->select = "sum(dollar) as sell";
        $transaction->where = "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%SELL%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );

        $dollar = $dollar - $transaction->resultarray[0]['sell'];

        return $dollar;
}

function CalculateSharesAvailable( $username, $symbol )
{
        $numbershares = 0;
	require_once( '../model/transaction.class.php' );
        $transaction = new transaction();
	$transaction->fieldspec['username']['extra_sql'] = "";
	$transaction->orderby = "";

        $transaction->select = "sum(numbershares) as buy";
        $transaction->where = "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%BUY%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $numbershares = $numbershares + $transaction->resultarray[0]['buy'];

        $transaction->select = "sum(numbershares) as drip";
        $transaction->where = "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%DIV%REINV%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $numbershares = $numbershares + $transaction->resultarray[0]['drip'];

        $transaction->select = "sum(numbershares) as split";
        $transaction->where = "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%SPLIT%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $numbershares = $numbershares + $transaction->resultarray[0]['split'];

        $transaction->select = "sum(numbershares) as sell";
        $transaction->where = "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%SELL%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );

        $numbershares = $numbershares - $transaction->resultarray[0]['sell'];

        return $numbershares;
}

function CalculateDollarsAvailableDate( $username, $transactiondate )
{
        $dollar = 0;
	require_once( '../model/transaction.class.php' );
        $transaction = new transaction();
	$transaction->fieldspec['username']['extra_sql'] = "";
	$transaction->orderby = "";

        $transaction->select = "sum(dollar) as buy";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%BUY%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $dollar = $dollar + $transaction->resultarray[0]['buy'];

        $transaction->select = "sum(dollar) as drip";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%DIV%REINV%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $dollar = $dollar + $transaction->resultarray[0]['drip'];

        $transaction->select = "sum(dollar) as split";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%SPLIT%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $dollar = $dollar + $transaction->resultarray[0]['split'];

        $transaction->select = "sum(dollar) as sell";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = 'CASH' and username = '" . $username . "' and transactiontype like '%SELL%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );

        $dollar = $dollar - $transaction->resultarray[0]['sell'];

        return $dollar;
}

function CalculateSharesAvailableDate( $username, $symbol, $transactiondate )
{
        $numbershares = 0;
	require_once( '../model/transaction.class.php' );
        $transaction = new transaction();
	$transaction->fieldspec['username']['extra_sql'] = "";
	$transaction->orderby = "";

        $transaction->select = "sum(numbershares) as buy";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%BUY%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $numbershares = $numbershares + $transaction->resultarray[0]['buy'];

        $transaction->select = "sum(numbershares) as drip";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%DIV%REINV%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $numbershares = $numbershares + $transaction->resultarray[0]['drip'];

        $transaction->select = "sum(numbershares) as split";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%SPLIT%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );
        ////echo "<br />";
        $numbershares = $numbershares + $transaction->resultarray[0]['split'];

        $transaction->select = "sum(numbershares) as sell";
        $transaction->where = "transactiondate <= '" . $transactiondate . "' and " . "stocksymbol = '$symbol' and username = '" . $username . "' and transactiontype like '%SELL%'";
        $transaction->Select();
	//var_dump( $transaction->querystring );
        //var_dump( $transaction->resultarray );

        $numbershares = $numbershares - $transaction->resultarray[0]['sell'];

        return $numbershares;
}


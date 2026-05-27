<?php

//20090804 KF
//Testing simple buy/sell of 1 stock based upon candlestick indicators

require_once( '../model/include_all.php' );
require_once( '../model/transaction.class.php' );
require_once( '../model/portfolio_daily.class.php' );
require_once( '../model/portfolio_history.class.php' );

//To be useable in portfolio_daily, need:
//	username
//	account
//	tradedate
//	bookvalue
//	marketvalue
//	cash on hand
function calcdaily( $user, $date, $data )
{
	$result = array();
	foreach( $data as $account => $details )
	{
		foreach( $details as $symbol => $values )
		{
			$result[$account]['bookvalue'] += $values['bookvalue'];
			$result[$account]['marketvalue'] += $values['marketvalue'];
			$result[$account]['username'] = $user;
			$result[$account]['tradedate'] = $date;
			$result[$account]['account'] = $account;
			if( $symbol == "CASH" )
				$result[$account]['cash'] += $values['bookvalue'];
			$result['ALL']['bookvalue'] += $values['bookvalue'];
			$result['ALL']['marketvalue'] += $values['marketvalue'];
			$result['ALL']['username'] = $user;
			$result['ALL']['tradedate'] = $date;
			$result[$account]['account'] = "ALL";
			if( $symbol == "CASH" )
				$result['ALL']['cash'] += $values['bookvalue'];
		}
	}
	return $result;
}

//Portfolio_history
//	username
//	tradedate
//	stocksymbol
//	numbershares
//	bookvalue
//	marketvalue
//	currentprice
//	profitloss
//	marketbook
//	percenttotalbookvalue
//	percenttotalmarketvalue
function calchistory( $user, $date, $data )
{
	$result = array();
		foreach( $data as $symbol => $values )
		{
			$result[$symbol]['currentprice'] = $values['currentprice'];
			$result[$symbol]['numbershares'] = $values['numbershares'];
			$result[$symbol]['profitloss'] =$values['marketvalue'] - $values['bookvalue'];
			$result[$symbol]['marketbook'] =$values['marketvalue'] / $values['bookvalue'];
			$result[$symbol]['bookvalue'] = $values['bookvalue'];
			$result[$symbol]['marketvalue'] = $values['marketvalue'];
			$result[$symbol]['username'] = $user;
			$result[$symbol]['stocksymbol'] = $symbol;
			$result[$symbol]['tradedate'] = $date;
			if( $symbol == "CASH" )
				$result[$symbol]['cash'] += $values['bookvalue'];
	
			$result['ALL']['currentprice'] = 0;
			$result['ALL']['numbershares'] = 0;
			$result['ALL']['bookvalue'] += $values['bookvalue'];
			$result['ALL']['marketvalue'] += $values['marketvalue'];
			$result['ALL']['profitloss'] = $result['ALL']['marketvalue'] - $result['ALL']['bookvalue'];
			$result['ALL']['marketbook'] = $result['ALL']['marketvalue'] / $result['ALL']['bookvalue'];
			$result['ALL']['username'] = $user;
			$result['ALL']['tradedate'] = $date;
			if( $symbol == "CASH" )
				$result['ALL']['cash'] += $values['bookvalue'];
		}
//	var_dump( $result );
	return $result;
}

function valuateportfolio( $user, $startdate, $startingcash, $tradedatearray, $actionarray = NULL )
{
	//go through technical analysis for this portfolio,
	//using the identified candlesticks sell or buy
	//half of ALL stocks or all cash.  When buying, will
	//buy equal dollar values of each share on the date
	//
	//DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
	$dayslag = 1;

	//Open a log file
	$flog = fopen( "../logs/" . $user . "." . date( 'ymdhs' ) . ".txt", "w" );
	fwrite( $flog, "Started portfolio valuation\n" );
	if( require_once( 'getmidprice.php' ))
	{
	}
	else exit( FAILURE );
	if( require_once( 'getcloseprice.php' ))
	{
	}
	else exit( FAILURE );
	//Get list of symbols for the user within transactions
	$ta = new transaction();
	$ta->fieldspec['username']['extra_sql'] = NULL;
	$ta->where = "username = '" .  $user .  "'";
	//$ta->select = "distinct symbol"
	$ta->orderby = "transactiondate asc";
	$ta->Select();
//	var_dump( $ta->querystring );

//To be useable in portfolio_daily, need:
//	username
//	account
//	tradedate
//	bookvalue
//	marketvalue
//	cash on hand
//Portfolio_history
//	username
//	tradedate
//	stocksymbol
//	numbershares
//	bookvalue
//	marketvalue
//	currentprice
//	profitloss
//	marketbook
//	percenttotalbookvalue
//	percenttotalmarketvalue

	$daily['ALL']['bookvalue'] = 0;
	$daily['ALL']['marketvalue'] = 0;
	$daily['ALL']['cash'] = 0;
	$currentdate = "";
//	var_dump( $ta->resultarray );
	$portfolio_daily = new portfolio_daily();
	$portfolio_history = new portfolio_history();
	foreach( $tradedatearray as $tradedate => $nexttradedate )
	{
		if( $nexttradedate >= $startdate AND $nexttradedate >= $ta->resultarray[0]['transactiondate'])
		{
			echo $currentdate . "\n";
			//Need a row for each date, for each account
			if( $currentdate != $nexttradedate )
			{
				//Need to sum up the running total and daily totals
						//accounts is by day, by account per symbol
					//sumALL
						//allaccounts is all accounts running total per symbol
						$history = calchistory( $user, $currentdate, $allaccounts );
					//sumAccounts
						//runningaccounts is by account running total per symbol
						$daily = calcdaily( $user, $currentdate, $runningaccounts );
				//Submit to _daily and _history
				$portfolio_history->InsertArray( $history );
				var_dump( $portfolio_history->errors );
				$portfolio_daily->InsertArray( $daily );
				$currentdate = $nexttradedate;
			}
			foreach( $ta->resultarray as $row )
			{
				if( $row['transactiondate'] == $nexttradedate )
				{
				
					if( $row['stocksymbol'] != 'CASH' )
						$shareprice = getcloseprice( $flog, $row['stocksymbol'], $nexttradedate );
					else
						$shareprice = "1";
					//add transaction to running total
					if( 
						( $row['transactiontype'] == "BUY" )
					   	OR ( $row['transactiontype'] == "TRANSFERIN" )
					)
					{
						$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['numbershares'] += $row['numbershares'];
						$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['bookvalue'] += $row['dollar'];
						$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['marketvalue'] = 
							$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['numbershares'] 
							* $shareprice;
						$runningaccounts[$row['account']][$row['stocksymbol']]['bookvalue'] += $row['dollar'];
						$runningaccounts[$row['account']][$row['stocksymbol']]['marketvalue'] = 
							$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['numbershares'] 
							* $shareprice;
						$allaccounts[$row['stocksymbol']]['numbershares'] += $row['numbershares'];
						$allaccounts[$row['stocksymbol']]['bookvalue'] += $row['dollar'];
						$allaccounts[$row['stocksymbol']]['marketvalue'] = 
							$allaccounts[$row['stocksymbol']]['numbershares'] 
							* $shareprice;
						$allaccounts[$row['stocksymbol']]['currentprice'] = $shareprice;
					}
					else
					//sub transaction from running total
					if(
						( $row['transactiontype'] == "SELL" )
						OR( $row['transactiontype'] == "TRANSFEROUT" )
					)
					{
						$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['numbershares'] -= $row['numbershares'];
						$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['bookvalue'] -= $row['dollar'];
						$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['marketvalue'] = 
							$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['numbershares'] 
							* $shareprice;
						$runningaccounts[$row['account']][$row['stocksymbol']]['bookvalue'] -= $row['dollar'];
						$runningaccounts[$row['account']][$row['stocksymbol']]['marketvalue'] = 
							$accounts[$nexttradedate][$row['account']][$row['stocksymbol']]['numbershares'] 
							* $shareprice;
						$allaccounts[$row['stocksymbol']]['numbershares'] -= $row['numbershares'];
						$allaccounts[$row['stocksymbol']]['bookvalue'] -= $row['dollar'];
						$allaccounts[$row['stocksymbol']]['marketvalue'] = 
							$allaccounts[$row['stocksymbol']]['numbershares'] 
							* $shareprice;
						$allaccounts[$row['stocksymbol']]['currentprice'] = $shareprice;
					}
				}
			}
		}
	}
return $accounts;
}


//TESTING
//build tradedatearray

require_once( 'buildtradedatesarray.php' );
$user = "candlestick_portfolio";
$user = "test";
$tradedatesarray = buildtradedatesarray();
$startdate = "1970-01-01";
$symbol = "IBM";
$startingcash = "1000.00";
$accountss = valuateportfolio( $user, $startdate, $startingcash, $tradedatesarray );
//var_dump( $accountss );

$fp = fopen( $user . ".accounts.txt", "w" );
$fpdetails = fopen( $user . ".accountsdetails.txt", "w" );
foreach( $accountss as $date => $accountarray )
{
	foreach( $accountarray as $symbol => $symboldetail )
	{
		//var_dump( $symbol );
/*
		fwrite( $fpdetails, "$date : 
					$symbol :: 
					$symboldetail['numbershares'] :: 
					$symboldetail['dollars'] 
					\n" );
		if( $symbol == "CASH" or $symbol == "ALL" )
			fwrite( $fp, "$date : $symbol :: $symboldetail['dollars'] \n" );
*/
	}
}

fclose( $fp );
fclose( $fpdetails );
?>

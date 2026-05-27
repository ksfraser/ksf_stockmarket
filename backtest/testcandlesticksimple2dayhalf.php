<?php

//20090804 KF
//Testing simple buy/sell of 1 stock based upon candlestick indicators

require_once( '../model/include_all.php' );

function testcandlesticksimple2dayhalf( $symbol, $startingcash, $tradedatearray, $actionarray )
{
	//go through technical analysis for this symbol,
	//using the identified candlesticks sell or buy
	//ALL stocks or all cash.
	//
	//DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS

	$user = "candlestick_simple2dayhalf";
	//Open a log file
	$flog = fopen( "../logs/" . $user . "." . date( 'ymdhs' ) . ".txt", "w" );
	 fwrite( $flog, "Started input variable valiudation\n" );
        if( $symbol == NULL )
        {
                fwrite( $flog, "Symbol NULL.  Exiting\n" );
                return FAILURE;
        }
        if( $startingcash == NULL )
        {
                fwrite( $flog, "Startingcash NULL.  Exiting\n" );
                return FAILURE;
        }
        if( $tradedatearray == NULL )
        {
                fwrite( $flog, "tradedatearray NULL.  Exiting\n" );
                return FAILURE;
        }
        if( $actionarray == NULL )
        {
                fwrite( $flog, "actionarray NULL.  Exiting\n" ); 
                return FAILURE;
        }
        if( !is_array($tradedatearray) )
        {
                fwrite( $flog, "tradedatearray not an array.  Exiting\n" );
                return FAILURE; 
        }
        if( count($tradedatearray) < 2 )
        {
                fwrite( $flog, "tradedatearray doesn't have enough rows.  Exiting\n" );
                return FAILURE;
        }
        if( !is_array($actionarray) )
        {
                fwrite( $flog, "actionarray not an array.  Exiting\n" ); 
                return FAILURE;
        }
        if( count($actionarray) < 2 )
        {
                fwrite( $flog, "actionarray doesn't have enough rows.  Exiting\n" ); 
                return FAILURE;
        }
        fwrite( $flog, "Variable valiudation OK\n" );


	fwrite( $flog, "Started portfolio construction\n" );

	//Add the user
	if( require_once( 'adduser.php' ))
	{
		$ret = adduser( $flog,
				$user,
				$surname = "Backtest Candlestick Simple", 
				$firstname = "Buy Sell half of all stock or cash",
				$emailaddress = "fraser.ks@gmail.com", 
				$password = "", 
				$roles_id = "4" 
			);
		if ($ret == FAILURE )
		{
			fwrite( $flog, "Couldn't create user\n" );
			exit( FAILURE );
		}
		fwrite( $flog, "Created user" . $user . "\n" );
	}
	
	//Add starting cash to portfolio
	if( require_once( 'account-transactions.php' ))
	{
		//fwrite( $flog, "Cleaning up old test data\n" );
		//cleanuser( $flog, $user );
		fwrite( $flog, "Adding cash to portfolio\n" );
		$ret = addcash( $flog, $user, $startingcash, "1970-01-01", "CAD", "TRADE" );
		if ($ret == FAILURE)
			exit( FAILURE );
	}
	//For the specified symbol, we need to go through technicalanalysis, 
	//get the candlesticks
	//and buy or sell depending on the specified candlestick
	//ALSO dependant on the dates in tradedates to find the 
	// buy and sell dates, and the prices out of stockprices 
	// on those dates.  Take the mid price between open and close
	if( require_once( '../model/technicalanalysis.class.php' ))
	{
		$ta = new technicalanalysis();
	}
	else exit( FAILURE );
	if( require_once( 'getmidprice.php' ))
	{
	}
	else exit( FAILURE );


	$ta->where = "symbol = '" . $symbol . "'";
	$ta->orderby = "date asc";
	$ta->Select();
	foreach( $ta->resultarray as $row )
	{
		$action = $actionarray[ $row['candlestick'] ];
		//get 2 days away
		$transactiondate = $tradedatearray[ $tradedatearray[$row['date']] ]; 
		fwrite( $flog, "Candlestick " . $row['candlestick'] . " has action " . $action . ".  Date " . $row['date'] . " and next transaction date " . $transactiondate . "\n" );
		$sharecost = getmidprice( $flog, $symbol, $transactiondate );
		if ($sharecost == "-1" )
		{
		}
		else if( $action == "buystock" )
		{
			//Get the dollars in cash in the portfolio
			$dollarsavailable = CalculateDollarsAvailable( $user );
			$dollarsavailable /= 2;
			fwrite( $flog, "Have $" . $dollarsavailable . " with which to buy shares\n" );
			
			//shares = dollars div sharecost (get whole shares)
			if ($sharecost == 0)
			{
				fwrite( $flog, "Invalid share price.  Can't buy when price 0\n" );
			}
			else if ($dollarsavailable > 0)
			{
				$numbershares = floor($dollarsavailable / $sharecost);
				$dollar = $numbershares * $sharecost;
				//dollar = shares * sharecost
				if( $numbershares > 0 )
					buystock($flog, $user, $symbol, $numbershares, $dollar, $transactiondate, "CAD", "CAD", "TRADE" );
			} else
				fwrite( $flog, "Can't buy shares without money\n" );
		}
		else if( $action == "sellstock" )
		{
			//get the number of shares in the portfolio
			$numbershares = CalculateSharesAvailable( $user, $symbol ) / 2;
			//dollar = number of shares * sharecost
			if( $numbershares > 0 )
			{
				$dollar = $numbershares * $sharecost;
				sellstock($flog, $user, $symbol, $numbershares, $dollar, $transactiondate, "CAD", "CAD", "TRADE" );
			}
		}
	}
return SUCCESS;
}


//TESTING
//build tradedatearray
/*require_once( 'buildtradedatesarray.php' );
$tradedatesarray = buildtradedatesarray();
$symbol = "IBM";
$startingcash = "1000.00";
testcandlesticksimple( $symbol, $startingcash, $tradedatesarray );
*/
?>

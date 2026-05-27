<?php

/***************************************************************
*
*       20111221 Money Management for trade strategies
*
*       @file strategoes.php
*       @brief module for money management strategies in investing
*
*       Money Management is used to manage your risk and the
*       resulting trade size.
*
*
*       USAGE:
*
***************************************************************/

/***************************************************************
*
*       Testing Results
*
***************************************************************/

echo __FILE__ . "\n";
require_once( 'data/generictable.php' );
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'strategiesConstants.php' );

require_once( 'moneymanagement.php' );  //dollars2invest and risksize

/***************************************************************
*       BEGIN
***************************************************************/
/*
Note: Risk and Money management rules should include:

   1. defining your trading float       (dollars2invest)
   2. setting a maximum loss            (risksize)
   3. setting you initial stops		(setinitialstoppricedelta)
   4. calculating your trade sizes.	(unitstopurchase)

NEVER TRADE MORE THAN x% OF YOUR PORTFOLIO IN ONE TRADE where x is customarily 10%.
userpref_tlv "Max_Pct_Portfolio_single_trade" (risksize)

# How much capital do you place on each trade.  	(dollars2invest)
# What is the heat of your trading.			(calculateHEAT)
# Capital preservation v. capital appreciation. 	(setinitialstoppricedelta)
# When do you experience expectation of success. 	(calcExpectancy)
# When must you take a loss to avoid larger losses.	(setinitialstoppricedelta)
# If you are on a losing streak do you trade the same.
# How must you prepare if trading both long and short positions. (channels)
# Does a portfolio of long and short allow one to trade more positions. (turtle max units)
# How is your trading adjusted with accumulated new profits.	(money goes into cash available for dollars2invest)
# How is volatility handled.				(setinitialstoppricedelta)
# Have you tested your bet sizing.			(backtest)

$portfolio_heat = $maxrisk * $numberopentrades;  //Each trading system has an optimum heat...
$expectancy = ( $percentagewin * $averagewinsize ) - ( $percentagelose * $averagelosesize );// If expectancy is negative, you don't want to use this strategy!!!

*/

/***************************************************************
*       @function setinitialstoppricedelta
*       @param string stocksymbol
*	@param date tradedate
*	@param functionptr (string name of fcn) pf_stoppricing
*       @see
*       @return float stop price delta for the purchase of the stock
***************************************************************/
/*@float@*/ function setinitialstoppricedelta( $stocksymblol, $tradedate, $pf_stoppricing )
{
	return $pf_stoppricing( $stocksymbol, $tradedate );
}
/***************************************************************
*       @function unitstopurchase
*	@param float initialstopdelta
*	@param float dollars to risk
*       @see
*       @return integer number of shares to purchase of the stock
***************************************************************/
/*@integer@*/ function unitstopurchase( $initialstopdelta, $dollars2risk )
{
	return floor( $dollars2risk / $initialstopdelta );
}

function return50( $symbol, $date )
{
	//Written for unit testing purposes, 
	//Using IBM which is trading well over 100$
	//so returning 50 hard coded for now
	return 50;
}

function strat_unittest()
{
        $_SESSION['username'] = "Kevin";
//      $_SESSION['account'] = "RRSP";

	$stocksymbol = "IBM";
	$tradedate = "2011-12-19";
	$dollars2risk = risksize( dollars2invest() );
	$stopdelta = setinitialstoppricedelta( $stocksymbol, $tradedate, "return50" );
	$units = unitstopurchase( $stopdelta, $dollars2risk );
	echo "Using stocksymbol IBM, tradedate 2011-12-19 and return50 the Dollars to risk " . $dollars2risk . " with a stop delta of " . $stopdelta . " results in a maximum of " . $units . " units to be purchased\n\n";
	return TRUE;
}

//echo "pre start_unittest()\n";
strat_unittest();
//echo "post start_unittest()\n";

?>

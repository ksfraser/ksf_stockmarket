<?php

/***************************************************************
*
*	20111220 Money Management for trade strategies
*
*	@file moneymanagement.php
*	@brief module for money management strategies in investing
*
*	Money Management is used to manage your risk and the
*	resulting trade size.
*
*
*	USAGE:
*	echo "Dollars to risk: " . risksize( dollars2invest() );
*
***************************************************************/

/***************************************************************
*
*	Testing Results
*
***************************************************************/

echo __FILE__ . "\n";
require_once( 'data/generictable.php' );
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'strategiesConstants.php' );

/***************************************************************
*	BEGIN            
***************************************************************/

/***************************************************************
*	@function dollars2risk
*	@param
*	@see
*	@return float dollar amount to invest
***************************************************************/
/*@float@*/ function dollars2invest()
{
	/***************************************************************
	*
	*	Variables used in this module
	*
	***************************************************************/
	$maxrisk = 0;
	$maxriskpct = 0;
	$maxsingletrade = 0;
	$maxsingletradepct = 0;
	$dollarsavailable = 0;
	$portfolio_marketvalue = 0;
	$portfolio_bookvalue = 0;
	$dollars2risk = 0;
	$market2risk = 0;
	$book2risk = 0;
	//$_SESSION['username'] (MANDATORY)
	//$_SESSION['transactiondate'] (optional)
	//$_SESSION['account'] (optional)
	
	/***************************************************************
	*
	*	Find default values for the user in terms of risk
	*	tolerance, size, etc
	*
	*	In any one trade we should never risk more than 1% of
	*	our total (all accounts) equity.  If we also consider 
	*	asset allocation, this would also include house, car,
	*	pension plans, etc.
	*
	***************************************************************/
	require_once( MODELDIR . '/userpref.class.php' );
	$userpref = new userpref();
	

	$pref = $userpref->RetrievePref( "Max_Pct_Portfolio_single_trade" );
	if( isset( $pref ))
	{
		$maxsingletradepct = $pref;
	}
	else
	{
		$maxsingletradepct = MM_SingleTradeRisk;
	}
	$maxsingletrade = $maxsingletradepct / 100;
	
	/***************************************************************
	*
	*	Portfolio size 
	*		Need to know the portfolio size to determine
	*		the maximum trade size
	*			marketvalue
	*			bookvalue
	*			cash available
	*			account
	*		However the portfolio is an up to date table
	*		so we need to calculate out of transactions
	*		when not looking at today's values.
	*
	***************************************************************/
	require_once( MODELDIR . '/portfolio.class.php' );
	$portfolio = new portfolio();
	require_once( MODELDIR . '/transaction.class.php' );
	$transaction = new transaction();
	
	$portfolio->Setusername( $_SESSION['username'] );
	$transaction->Setusername( $_SESSION['username'] );
	//Either a date set or todays date
	if( isset( $_SESSION['transactiondate'] ))
		$transaction->Settransactiondate( $_SESSION['transactiondate'] );
	else
		$transaction->Settransactiondate( date( 'Y-m-d' ) );
	if( isset( $_SESSION['account'] ))
		$transaction->Setaccount( $_SESSION['account'] ); //OK to be ''
	else
		$transaction->Setaccount( '' ); //OK to be ''
	$dollarsavailable = $transaction->CalculateDollarsAvailableDate();
	//echo "Dollars available" . $dollarsavailable . "\n";
	
	if( !isset( $_SESSION['transactiondate'] ))
	{
		//using today's date so we can use portfolio for book and market
		if( isset( $_SESSION['account'] ) AND "" <> $_SESSION['account'] )
			$portfolio->Setaccount( $_SESSION['account'] ); //NOT OK to be ''
		else
		{
			$portfolio->Setaccount( '' ); //OK to be ''
			$_SESSION['account'] = '';
		}
		if( !isset( $_SESSION[ $_SESSION['account'] ]['portfolio_marketvalue'] ))
		{
			if( $portfolio->account == "" )
				$portfolio->account = NULL;
			$portfolio->fieldspec['username']['extra_sql'] = "";
			$portfolio->select = "sum(marketvalue) as portfolio_marketvalue, sum(bookvalue) as portfolio_bookvalue";
			$portfolio->GetVARRow();
			//echo $portfolio->querystring . "\n";
			$_SESSION[ $_SESSION['account'] ]['portfolio_marketvalue'] = $portfolio->resultarray[0]['portfolio_marketvalue'];
			$_SESSION[ $_SESSION['account'] ]['portfolio_bookvalue'] = $portfolio->resultarray[0]['portfolio_bookvalue'];
		}
	}
	

	if( isset( $dollarsavailable ))
	{
		//Risk a maximum of maxsingletrade% of the portfolio or dollarsavailable, which ever is less
		//maxsingletrade
		$dollars2invest = min( $dollarsavailable, min( $_SESSION[ $_SESSION['account'] ]['portfolio_bookvalue'], $_SESSION[ $_SESSION['account'] ]['portfolio_marketvalue'] ) * $maxsingletrade );
		//echo "Dollars available ( " . $dollarsavailable . " ) to invest " . $dollars2invest . "\n";
	}
	return floor($dollars2invest);	
}

/***************************************************************
*	@function risksize
*	@param float dollars2risk
*	@see
*	@return float dollar amount to risk
***************************************************************/
function risksize( $dollars2risk )
{
	require_once( MODELDIR . '/userpref.class.php' );
	$userpref = new userpref();

	$pref = $userpref->RetrievePref( "Money_Management_Maxrisk_pct" );
	if( isset( $pref ))
	{
		$maxriskpct = $pref;
	}
	else
	{
		$maxriskpct = MM_Maxrisk;
	}
	$maxrisk = $maxriskpct / 100;

	if( isset( $_SESSION[ $_SESSION['account'] ]['portfolio_marketvalue'] ))
		$market2risk = $_SESSION[ $_SESSION['account'] ]['portfolio_marketvalue'] * $maxrisk;
	else
		$market2risk = $dollars2risk / 10;
	if( isset( $_SESSION[ $_SESSION['account'] ]['portfolio_bookvalue'] ))
		$book2risk = $_SESSION[ $_SESSION['account'] ]['portfolio_bookvalue'] * $maxrisk;
	else
		$book2risk = $dollars2risk / 10;
	if( $dollars2risk > $book2risk )
		$dollars2risk = $book2risk;
	if( $dollars2risk > $market2risk )
		$dollars2risk = $market2risk;
	return floor($dollars2risk);	
}

/*
//stopprice is determined through a strategy i.e. turtle's
$stopperunit = $shareprice - $stopprice;
$numberunits = $dollars2risk / $stopperunit;
$portfolio_heat = $maxrisk * $numberopentrades;  //Each trading system has an optimum heat...
$expectancy = ( $percentagewin * $averagewinsize ) - ( $percentagelose * $averagelosesize );// If expectancy is negative, you don't want to use this strategy!!!
*/

/*

Note: Risk and Money management rules should include:

   1. defining your trading float  	(dollars2invest)
   2. setting a maximum loss		(risksize)
   3. setting you initial stops
   4. calculating your trade sizes.



NEVER TRADE MORE THAN x% OF YOUR PORTFOLIO IN ONE TRADE where x is customarily 10%.
userpref_tlv "Max_Pct_Portfolio_single_trade"

# How much capital do you place on each trade.
# What is the heat of your trading.
# Capital preservation v. capital appreciation.
# When do you experience expectation of success.
# When must you take a loss to avoid larger losses.
# If you are on a losing streak do you trade the same.
# How must you prepare if trading both long and short positions.
# Does a portfolio of long and short allow one to trade more positions.
# How is your trading adjusted with accumulated new profits.
# How is volatility handled.
# How do you prepare yourself psychologically.
# Have you tested your bet sizing.

	



*/

function MM_unittest()
{
	$_SESSION['username'] = "Kevin";
//	$_SESSION['account'] = "RRSP";
	$d = dollars2invest();
	var_dump( $_SESSION );
	echo "Dollars to invest: " . $d . "\n";
	$r = risksize( $d );
	echo "Dollars to risk: " . $r . "\n";
	//SHORT FORM
	// echo "Dollars to risk: " . risksize( dollars2invest() );
}

//MM_unittest();
?>

<?php

/******************************************************************
*
*	20111207 KF 4 week rule
*	Buy if the price exceeds the highs of the 
*	four preceding full calendar weeks and 
*	liquidate open positions when the price falls below 
*	the lows of the four preceding full calendar weeks.
*
*********************************************************************/
/*******TEST RESULTS*******************
*
*	20111208 KF Tested OK
*		Made some changes to the functions in stockprices
*
*	20111207 KF Work to be done
*		When the close is the high, not matching properly.
*		When there is no data available for that day, the close is 
*		 blank which is lower than the 20 so a SELL is indicated
*
**************************************/

echo __FILE__ . "\n";
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
require_once( 'strategiesConstants.php' );



function fourweekrule( $symbol, $date )
{
//	echo "4weekrule\n";
	
 	require_once( '../model/stockprices.class.php' );
	$stockprices = new stockprices();
//	echo "Call higher\n";
	if ( $stockprices->closehigherthan20high( $symbol, $date ) )
	{
//		echo "BUY $symbol\n";
		return BUY;
	}
	else
//		echo "not higher\n";
	//echo "Call lower\n";
	if ( $stockprices->closelowerthan20low( $symbol, $date ) )
	{
//		echo "SELL $symbol\n";
		return SELL;
	}
	else
//		echo "not lower\n";
	echo "Do nothing with $symbol\n";
	return HOLD;
}

//Unit Testing
$pass = 0;
$fail = 0;
function unittestcheck( $symbol, $date, $action )
{
	global $pass;
	global $fail;
	//echo "$symbol on $date for $action\n";

	if( ($symbol == 'IBM' ) AND ( $date == '2011-12-01' ) AND ( $action == BUY))
		$pass++;
	else if (($symbol == 'CP' ) AND ( $date == '2011-12-01' ) AND ( $action == HOLD))
		$pass++;
	else if (($symbol == 'BPF-UN' ) AND ( $date == '2011-12-01' ) AND ( $action == BUY))
		$pass++;
	else if (($symbol == 'RUS' ) AND ( $date == '2011-12-01' ) AND ( $action == HOLD))
		$pass++;
	else if (($symbol == 'CNR' ) AND ( $date == '2011-12-01' ) AND ( $action == HOLD))
		$pass++;
	else
		$fail++;
	//echo "Pass $pass Fail $fail\n";
}
function unittestvalidate()
{
	global $pass;
	global $fail;
	if( $fail > 0 )
		echo "Unit test failed $fail tests!\n";
	else
		echo "Unit test passed $pass tests!\n";
}
$symbol = "IBM";
$date = '2011-12-01' ;
$action = fourweekrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
	echo "BUY $symbol\n";
if( $action == SELL )
	echo "SELL $symbol\n";
$symbol = "CP";
$action = fourweekrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
	echo "BUY $symbol\n";
if( $action == SELL )
	echo "SELL $symbol\n";
$symbol = "BPF-UN";
$action = fourweekrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
	echo "BUY $symbol\n";
if( $action == SELL )
	echo "SELL $symbol\n";
$symbol = "CNR";
$action = fourweekrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
	echo "BUY $symbol\n";
if( $action == SELL )
	echo "SELL $symbol\n";
$symbol = "RUS";
$action = fourweekrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
	echo "BUY $symbol\n";
if( $action == SELL )
	echo "SELL $symbol\n";
unittestvalidate();

?>

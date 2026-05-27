//Often, two or more of these forms of indicators will be combined in the creation of a rule. For example, the MA crossover system uses two moving average parameters, the long-term and the short-term, to create a rule: "buy when the short-term crosses above the long term, and sell when the opposite is true." In other cases, a rule uses only one indicator. For example, a system might have a rule that forbids any buying unless the relative strength is above a certain level. But it is a combination of all these kinds of rules that makes a trading system. 


<?php

/********************************************************
*
*	20111208 KF MA Crossover rule
*
*	TL;DR - short > long == BUY.  short < long == SELL.  
*		I suppose the rule should really be at the
* 		crossover itself, but this in general is 
*		probably a good enough indicator.  
*		Backtesting will tell.
*********************************************************/
/********************************************************
*
*	20111208 KF UNIT TEST
*		There is no valid data to test against.
*		setValues is setting values if they exist
*		logic itself appears to work for do nothing
*
*	20111209 KF scripts/technicalanalysis/calculatemovingaverages.php
*		should populate the data this script is dependant upon.
*		Script is running, so will have to wait and see.
*
*********************************************************/
echo __FILE__ . "\n";
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
require_once( 'strategiesConstants.php' );

function macrossoverrule( $symbol, $date )
{
	require_once( MODELDIR . "/technicalanalysis.class.php" );
	$ta = new technicalanalysis();
	$ta->Setdate( $date );
	$ta->Setsymbol( $symbol );
	$ta->setValues();
	//var_dump( $ta );

	$ma12 = $ta->Getexpmovingaverage12();
	$ma26 = $ta->Getexpmovingaverage26();

	echo "Averages 12: $ma12 and 26: $ma26\n";

	if( $ma12 > $ma26 )
	{
		echo "SELL $symbol\n";
		return SELL;
	}
	else if( $ma12 < $ma26 )
	{
		echo "BUY $symbol\n";
		return BUY;
	}
        echo "Do nothing with $symbol\n";
        return HOLD;
}

//UNIT TEST
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
        else if (($symbol == 'BMO' ) AND ( $date == '2011-12-01' ) AND ( $action == BUY))
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
$date = '1995-06-20' ;
$date = '2011-06-20' ;
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
$symbol = "CP";
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
$symbol = "BMO";
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
$symbol = "CNR";
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
$symbol = "AAPL";
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
$symbol = "ABD";
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
$symbol = "RUS";
$action = macrossoverrule( $symbol, $date );
unittestcheck( $symbol, $date, $action );
if( $action == BUY )
        echo "BUY $symbol\n";
if( $action == SELL )
        echo "SELL $symbol\n";
unittestvalidate();


?>

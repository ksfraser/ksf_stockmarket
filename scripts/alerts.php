<?php

//20101217 KF Replaced (int) with (float) as there was rounding occuring
//in the conversion from strings to ints.  Besides, dollar values need 
//the decimal place that the ints didn't have.

/* **********************************************************************************************************
*
*	The following functions are in this script
*
function EmailAlert( $username, $header, $msg )
function testfcn( $username, $idstockinfo, $v1, $v2 )
function currentpricegreaterthan( $username, $idstockinfo, $v1, $v2 )
function currentpricelessthan( $username, $idstockinfo, $v1, $v2 )
function currentpricebetween( $username, $idstockinfo, $v1, $v2 )
function averagevolumelessthan( $username, $idstockinfo, $v1, $v2 )
function averagevolumegreaterthan( $username, $idstockinfo, $v1, $v2 )
function yearhighlessthan( $username, $idstockinfo, $v1, $v2 )
function yearhighgreaterthan( $username, $idstockinfo, $v1, $v2 )
function yearlowlessthan( $username, $idstockinfo, $v1, $v2 )
function yearlowgreaterthan( $username, $idstockinfo, $v1, $v2 )
function highlessthan( $username, $idstockinfo, $v1, $v2 )
function highgreaterthan( $username, $idstockinfo, $v1, $v2 )
function lowlessthan( $username, $idstockinfo, $v1, $v2 )
function lowgreaterthan( $username, $idstockinfo, $v1, $v2 )
function stocknotupdatedsince( $username, $idstockinfo, $v1, $v2 )
function alertretractment( $username, $idstockinfo, $days, $percentage )
function alertadvancement( $username, $idstockinfo, $days, $percentage )
*
**********************************************************************************************************/

echo __FILE__;
echo "\n";
//These alerts will be called from processalerts.php
//Each function must take the following variables:
//	username
//	idstockinfo
//	value1
//	value2
//
//Each function should do 1 of 2 things when the alert triggers
//	Email the user; or
//	Place an alert message on their screens.
//Since I haven't built a mechanism to put the alerts up yet,
//each should email to start with.

define( 'NOTRAISED', 0 );
define( 'RAISED', 1 );
//echo "start of alerts.php\n";

require_once( 'include_all.php' );
//echo "required include_all.php\n";
require_once( $MODELDIR . '/stockinfo.class.php' );
//echo "required stockinfo.class.php\n";

//20110123 KF Moving to common so that other scripts can use also
require_once( 'common/EmailAlert.php' );
//!20110123

function testfcn( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	var_dump( $stock->resultarray );
	$emailresult = EmailAlert( $username, "Testfcn triggered" );
	return NOTRAISED;
}

function currentpricegreaterthan( $username, $idstockinfo, $v1, $v2 )
{
	//echo "1 ";
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	//echo "2 ";
	if ( (float)$stock->resultarray[0]['currentprice'] > (float)$v1 )
	{
		//echo "3 ";
		$subject = $stock->resultarray[0]['corporatename'] . "'s price " . $stock->resultarray[0]['currentprice'] . " is greater than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function currentpricelessthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	//echo $stock->resultarray[0]['corporatename'] . "'s price of " . $stock->resultarray[0]['currentprice'] . " compared to " . $v1 . "\n";
	if ( (float)$stock->resultarray[0]['currentprice'] < (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s price " . $stock->resultarray[0]['currentprice'] . " is less than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	else
		//echo "Current price not less than criteria\n";
	return NOTRAISED;
}

function currentpricebetween( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( ( (float)$stock->resultarray[0]['currentprice'] > (float)$v1 )
	    AND ( (float)$stock->resultarray[0]['currentprice'] < (float)$v2 ) )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s price " . $stock->resultarray[0]['currentprice'] . " is between alert value " . $v1 . " and " . $v2 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function averagevolumelessthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['averagevolume'] < (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s volume " . $stock->resultarray[0]['averagevolume'] . " is less than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function averagevolumegreaterthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['averagevolume'] > (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s volume " . $stock->resultarray[0]['averagevolume'] . " is greater than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function yearhighlessthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['yearhigh'] < (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s yearhigh " . $stock->resultarray[0]['yearhigh'] . " is less than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function yearhighgreaterthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['yearhigh'] > (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s yearhigh " . $stock->resultarray[0]['yearhigh'] . " is greater than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function yearlowlessthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['yearlow'] < (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s yearlow " . $stock->resultarray[0]['yearlow'] . " is less than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function yearlowgreaterthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['yearlow'] > (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s yearlow " . $stock->resultarray[0]['yearlow'] . " is greater than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function highlessthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['high'] < (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s high " . $stock->resultarray[0]['high'] . " is less than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function highgreaterthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['high'] > (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s high " . $stock->resultarray[0]['high'] . " is greater than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function lowlessthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['low'] < (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s low " . $stock->resultarray[0]['low'] . " is less than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

function lowgreaterthan( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	if ( (float)$stock->resultarray[0]['low'] > (float)$v1 )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s low " . $stock->resultarray[0]['low'] . " is greater than alert value " . $v1 . "\n";
		$header = "Stock Alert for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

//Eventum project finance issue #12
//Allow user to be alerted that a stock isn't being updated
function stocknotupdatedsince( $username, $idstockinfo, $v1, $v2 )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	$dateofInterest = time() - ((float)$v1 * 24 * 60 * 60);
	//echo 'Next Week: '. date('Y-m-d', $nextWeek) ."\n";
	if ( (float)$stock->resultarray[0]['asofdate'] < $dateofInterest )
	{
		$subject = $stock->resultarray[0]['corporatename'] . "'s last update was " . $stock->resultarray[0]['asofdate'] . " which is older than alert value " . $v1 . "\n";
		$header = "Stock Alert NO RECENT UPDATE for " . $stock->resultarray[0]['corporatename'] . "\n";
		$emailresult = EmailAlert( $username, $header, $subject );
		return RAISED;
	}
	return NOTRAISED;
}

//!#12

//20090807 KF
//Eventum #146 Alert on retractments
//Adding alerts to check for a price that has retracted a certain percentage in so many days

function alertretractment( $username, $idstockinfo, $days, $percentage )
{
	//echo "Username: " . $username . " idStockInfo: " . $idstockinfo . " Days: " . $days . " Percentage: " . $percentage . "\n";
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	$symbol = $stock->resultarray[0]['stocksymbol'];
	//echo "Symbol: " . $symbol . "\n";
	//var_dump( $stock->resultarray[0] );
        require_once( 'technicalanalysis/retractment.php' );
	$retracted = percentretractment( $symbol, $days );
//	echo "Retracted $retracted";
        if ( $percentage <= $retracted )
	{
		$subject = "RETRACTMENT Alert: $symbol retracted more than $percentage in the last $days days ";
		$header = $symbol . " Retractment Alert - " . $percentage . "% in " . $days . " days";
		$emailresult = EmailAlert( $username, $header, $subject );
                return RAISED;
	}
        else
                return NOTRAISED;
}

function alertadvancement( $username, $idstockinfo, $days, $percentage )
{
	$stock = new stockinfo();
	$stock->where = "idstockinfo = '" . $idstockinfo . "'";
	$stock->Select();
	$symbol = $stock->resultarray[0]['stocksymbol'];
        require_once( 'technicalanalysis/advancement.php' );
	$advanced = percentadvancement( $symbol, $days );
//	echo "Advanced $advanced";
        if ( $percentage <=$advanced )
	{
		$subject = "ADVANCEMENT Alert: $symbol advanced more than $percentage in the last $days days ";
		$header = $symbol . " advancement Alert - " . $percentage . " % in " . $days . " days";
		$emailresult = EmailAlert( $username, $header, $subject );
                return RAISED;
	}
        else
                return NOTRAISED;
}

//!146

//TEST
/*
alertadvancement( "kevin", "SLV", "20", "10" );
alertadvancement( "kevin", "SLV", "20", "5" );
alertadvancement( "kevin", "SLV", "55", "10" );
alertretractment( "kevin", "SLV", "20", "5" );
alertretractment( "kevin", "SLV", "20", "10" );
alertretractment( "kevin", "SLV", "55", "10" );
*/
?>

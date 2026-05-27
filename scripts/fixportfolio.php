<?php

//20110122 KF Looks like functions to do all this is now in the portfolio class
//      Updateprofit
//      Updatemarketbook
//      Updatedividendpercentbookvalue
//      Updateannualdividend
//      Updatedividendpercentmarketvalue
//      Updatedividendyeild
//      Updatepercenttotalmarketvalue
//      Updatepercenttotalbookvalue
//      Updatepercenttotaldividend
//      Updatebookvalue
//      Updatedividendbookvalue
//      Updatenumbershares
//      Updatecurrentprice
//      Updatemarketvalue
//      Updatedividendpershare
//      Updateyeild

//2008-04-22 Added unset commands to reduce memory usage since the script is erroring out.

//20081226 Eventum project finance issue #31
//Divide by zero errors
//add in the if XX <> 0 on the divisors.

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;
require_once( 'triggered.php' );

require_once( 'portfolio.class.php' );
echo __FILE__;

//20110122 KF portfolio class now performs all of this
$portfolio = new portfolio;
$portfolio->UpdatePortfolios();
exit();


//2008-04-22 Added unset commands to reduce memory usage since the script is erroring out.

//20081226 Eventum project finance issue #31
//Divide by zero errors
//add in the if XX <> 0 on the divisors.

require_once( $MODELDIR . '/stockinfo.class.php' );
require_once( $MODELDIR . '/transaction.class.php' );

$sumquery = 'SELECT sum(bookvalue) as booksum, sum(marketvalue) as marketsum, sum(annualdividend) as dividendsum, username FROM portfolio group by username';
$portfolio->querystring = $sumquery;
$portfolio->GenericQuery();
//var_dump( $portfolio->resultarray );
foreach( $portfolio->resultarray as $results )
{
//	var_dump( $results );
	$sum[$results['username']]['booksum'] = $results['booksum'];
	$sum[$results['username']]['marketsum'] = $results['marketsum'];
	$sum[$results['username']]['dividendsum'] = $results['dividendsum'];
}
unset( $portfolio->resultarray);
$stockinfo = new stockinfo;
$stockinfo->querystring = "SELECT * from stockinfo";
$stockinfo->GenericQuery();
foreach( $stockinfo->resultarray as $results )
{
	$stock[$results['stocksymbol']]['price'] = $results['currentprice'];
	$stock[$results['stocksymbol']]['annualdividendpershare'] = $results['annualdividendpershare'];
}
unset( $stockinfo );

/*
$transaction = new transaction;
//20100402 The use of the results below suggest we
//are trying to get a sum of the net shares.  Need to do
//the math of buy, sell, etc
$transaction->querystring = "";
$transaction->GenericQuery();
foreach( $transaction->resultarray as $results )
{
	$numshares[$results['username']][$results['stocksymbol']] = $results['shares'];
} 
unset( $transaction );
*/

$portfolio->querystring = "SELECT * FROM portfolio";
$portfolio->GenericQuery();
//var_dump( $portfolio->resultarray );
foreach( $portfolio->resultarray as $results )
{
	$currentuser = $results['username'];
	$_SERVER['PHP_AUTH_USER'] = $results['username'];
	$update['idportfolio'] = $results['idportfolio'];
	//Get the number of shares is correct
	$stocksymbol = $results['stocksymbol'];
	$update['numbershares'] = CalculateNumberShares( $currentuser, $stocksymbol );
	$update['bookvalue'] = Calculatebookvalue( $currentuser, $stocksymbol );
	$update['dividendbookvalue'] = $update['bookvalue'] - Calculatedividendbookvalue( $currentuser, $stocksymbol );
	$update['currentprice'] = $stock[$stocksymbol]['price'];
	$update['marketvalue'] = Calculatemarketvalue( $update['numbershares'],  $update['currentprice'] );
	$update['profitloss'] = $update['marketvalue'] - $update['bookvalue'];
	$update['marketbook'] = Calculatemarketbook( $update['marketvalue'], $update['bookvalue'] );
	$update['annualdividendpershare'] = $stock[$stocksymbol]['annualdividendpershare'];
	if( ($update['bookvalue'] * $update['numbershares']) <> 0 )
	$update['dividendpercentbookvalue'] = $update['annualdividendpershare'] / $update['bookvalue'] * $update['numbershares'] * 100;
	if( ($update['marketvalue'] * $update['numbershares']) <> 0 )
	$update['dividendpercentmarketvalue'] = $update['annualdividendpershare'] / $update['marketvalue'] * $update['numbershares'] * 100;
	if( $update['currentprice'] <> 0 )
	$update['dividendyield'] = $update['annualdividendpershare'] / $update['currentprice'] * 100;
	if( $sum[$currentuser]['booksum'] <> 0 )
	$update['percenttotalbookvalue'] = $update['bookvalue'] / $sum[$currentuser]['booksum'] * 100;
	if( $sum[$currentuser]['marketsum'] <> 0 )
	$update['percenttotalmarketvalue'] = $update['marketvalue'] / $sum[$currentuser]['marketsum'] * 100;
	$update['annualdividend'] = $update['annualdividendpershare'] * $update['numbershares'];
	if( $sum[$currentuser]['dividendsum'] <> 0 )
	$update['percenttotaldividend'] = $update['annualdividend'] / $sum[$currentuser]['dividendsum'] * 100;
	$portfolio->Update( $update );

	//var_dump( $update );

}

exit(0);	

?>

<?php
echo __FILE__;

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;
require_once( 'triggered.php' );

require_once( $MODELDIR . '/portfolio_history.class.php' );

$sumquery = 'SELECT sum(bookvalue) as booksum, sum(marketvalue) as marketsum, sum(annualdividend) as dividendsum, username FROM portfolio group by username';
$portfolio = new portfolio_history;
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
require_once( $MODELDIR . '/stockinfo.class.php' );
$stockinfo = new stockinfo;
$stockinfo->querystring = "SELECT * from stockinfo";
$stockinfo->GenericQuery();
foreach( $stockinfo->resultarray as $results )
{
	$stock[$results['stocksymbol']]['price'] = $results['currentprice'];
	$stock[$results['stocksymbol']]['annualdividendpershare'] = $results['annualdividendpershare'];
}

require_once( $MODELDIR . '/transaction.class.php' );
$transaction = new transaction;
$transaction->querystring = "";
$transaction->GenericQuery();
foreach( $transaction->resultarray as $results )
{
	$numshares[$results['username']][$results['stocksymbol']] = $results['shares'];
} 

$portfolio->querystring = "SELECT * FROM portfolio";
$portfolio->GenericQuery();
//var_dump( $portfolio->resultarray );
foreach( $portfolio->resultarray as $results )
{
	$currentuser = $results['username'];
	$_SERVER['PHP_AUTH_USER'] = $results['username'];
	$update['idportfolio_history'] = $results['idportfolio_history'];
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
	$update['dividendpercentbookvalue'] = $update['annualdividendpershare'] / $update['bookvalue'] * $update['numbershares'] * 100;
	$update['dividendpercentmarketvalue'] = $update['annualdividendpershare'] / $update['marketvalue'] * $update['numbershares'] * 100;
	$update['dividendyield'] = $update['annualdividendpershare'] / $update['currentprice'] * 100;
	$update['percenttotalbookvalue'] = $update['bookvalue'] / $sum[$currentuser]['booksum'] * 100;
	$update['percenttotalmarketvalue'] = $update['marketvalue'] / $sum[$currentuser]['marketsum'] * 100;
	$update['annualdividend'] = $update['annualdividendpershare'] * $update['numbershares'];
	$update['percenttotaldividend'] = $update['annualdividend'] / $sum[$currentuser]['dividendsum'] * 100;
	$portfolio->Update( $update );

	//var_dump( $update );

}	

?>

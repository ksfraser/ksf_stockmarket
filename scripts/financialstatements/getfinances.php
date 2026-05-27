<?php

//include_once( $MODELDIR . '/fin_statement.class.php' );
//include_once( $MODELDIR . '/evalmarket.class.php' );
//include_once( $MODELDIR . '/quarter_statement.class.php' );
//include_once( $MODELDIR . '/ratios.class.php' );
//require_once( $MODELDIR . '/bondrate.class.php' );
//include_once( '../fundamentalanalysis/getfuturevalue.php' );

include_once( 'include_all.php' );
require_once( '../fundamentalanalysis/getdiscountrate.php' );
require_once( '../getbondratearray.php' );
require_once( 'getstockfinancial.php' );
include_once( $MODELDIR . '/stockinfo.class.php' );

//$market = new fin_statement();
//$evalmarket = new evalmarket();
//$quarter = new quarter_statement();
//$ratios = new ratios();
//$bondrate = new bondrate();

$stockinfo = new stockinfo();
//Get list of stocks to eval
$stockinfo->querystring = "Select s.stocksymbol, e.googlesymbol, s.idstockinfo, s.currentprice from stockinfo s, stockexchange e where s.stockexchange = e.idstockexchange order by s.idstockinfo desc";
$stockinfo->GenericQuery();

$year = date( "Y" );
$bonddate = (string)($year + 30) . "-01-01";

	$discountrate = getdiscountrate( $year );
	$bondratearray = getbondratearray( "10" );

foreach( $stockinfo->resultarray as $results )
{

/* Moved these into getstockfinancial	
*	//var_dump( $results );
*	$result = getstatement( $results['stocksymbol'], $results['googlesymbol'], $results['idstockinfo'] );
*	$result['marketcap'] = $result['outstandingshare'] * $results['currentprice'];
*	$result['discountrate'] = $discountrate;
*	$future = getfuturevalue( $result, $bondrate->resultarray );
*	$result['value'] = $future['value'];
*	$result['marginsafety'] = $future['marginsafety'];
*	if( $result != NULL )
*		$market->Insert( $result );
*		$evalmarket->Insert( $result );
*		$stockinfo->Update( $result ); //update the company name.
*		$quarter->Insert( $result['quarter'] );
* //Eventum #152
*		$ratios->Insert( $result );
* //!#152
*/
	getstockfinancial( $results, $bondratearray );
}

?>



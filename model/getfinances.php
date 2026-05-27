<?php

include_once( 'parse_financials.php' );
include_once( 'include_all.php' );
include_once( 'fin_statement.class.php' );
$market = new fin_statement();
include_once( 'stockinfo.class.php' );
$stockinfo = new stockinfo();

//Get list of stocks to eval
$stockinfo->querystring = "Select s.stocksymbol, e.googlesymbol, s.idstockinfo from stockinfo s, stockexchange e where s.stockexchange = e.idstockexchange order by s.idstockinfo desc";
$stockinfo->GenericQuery();

foreach( $stockinfo->resultarray as $results )
{	
	//var_dump( $results );
	$result = getstatement( $results['stocksymbol'], $results['googlesymbol'], $results['idstockinfo'] );
	if( $result != NULL )
		$market->Insert( $result );
}

?>



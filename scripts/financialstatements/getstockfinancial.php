<?php

//include_once( 'parse_financials.php' );
include_once( 'include_all.php' );

include_once( $MODELDIR . '/fin_statement.class.php' );
include_once( $MODELDIR . '/evalmarket.class.php' );
include_once( $MODELDIR . '/quarter_statement.class.php' );
include_once( $MODELDIR . '/stockinfo.class.php' );
include_once( $MODELDIR . '/ratios.class.php' );
include_once( $MODELDIR . '/iplace_calc.class.php' );
require_once( '../fundamentalanalysis/getdiscountrate.php' );

include_once( '../fundamentalanalysis/getfuturevalue.php' );
require_once( 'googledownloadstatement.php' );
require_once( 'converttags.php' );
require_once( 'calculateratios.php' );
require_once( 'calculatefinancials.php' );
require_once( 'google-findata2array.php' );


function doannualinserts( $result )
{
	$market = new fin_statement();
	$evalmarket = new evalmarket();
	$stockinfo = new stockinfo();
	$ratios = new ratios();
	$iplace = new iplace_calc();

	$market->Insert( $result );
        $evalmarket->Insert( $result );
        $stockinfo->Update( $result ); //update the company name.
//Eventum #152
        $ratios->Insert( $result );
	$iplace->Insert( $result );
//!#152
	unset( $market );
	unset( $evalmarket );
	unset( $stockinfo );
	unset( $ratios );
	unset ($iplace );
	return;
}

function doquarterlyinserts( $result )
{
	$quarter = new quarter_statement();
        $quarter->Insert( $result );
	unset( $quarter );
	return;
}

function extractannual( $filename )
{
/*
	$annual = findata2xml( $filename, "incannualdiv" );
	$annual .= findata2xml( $filename, "balannualdiv" );
	$annual .= findata2xml( $filename, "casannualdiv" );
	$annual = "<?xml version='1.0'?><document>" . converttags( $annual ) . "</document>";
	$result = xml2findata( $annual );
*/
	$annuali = findata2array( $filename, "incannualdiv" );
	if( NULL == $annuali )
		return NULL;
	$annualb = findata2array( $filename, "balannualdiv" );
	if( NULL == $annualb )
		return NULL;
	$annualc = findata2array( $filename, "casannualdiv" );
	if( NULL == $annualc )
		return NULL;
	$result = array_merge( $annuali, $annualb, $annualc );
	return $result;
}

function extractquarterly( $filename )
{
/*
	$quarterly = findata2xml( $filename, "incinterimdiv" );
	$quarterly .= findata2xml( $filename, "balinterimdiv" );
	$quarterly .= findata2xml( $filename,  "casinterimdiv");
	$quarterly = "<?xml version='1.0'?><document>" . converttags( $quarterly ) . "</document>";
	$qupdate = xml2findata( $quarterly );
	return $qupdate;
*/
	$interimi = findata2array( $filename, "incinterimdiv" );
	$interimb = findata2array( $filename, "balinterimdiv" );
	$interimc = findata2array( $filename, "casinterimdiv" );
	$result = array_merge( $interimi, $interimb, $interimc );
	return $result;


}

function getstockfinancial( $results, $bondratearray )
{
/* TESTING
	if( $results['stocksymbol'] != "BPF-UN" )
	//if( $results['stocksymbol'] != "BAM-A" )
	{
		echo "Exit on wrong symbol";
		return;
	}
*/
	$filename = googledownloadstatement( $results['stocksymbol'], $results['googlesymbol'] );
	if( $filename == NULL )
		return;
	$annual = extractannual( $filename );
	$annualfin = calculatefinancials( $annual );
	$result = calculateratios( $annualfin );
	$currentyear = date( 'Y' );
        if( $result != NULL )
	{
		//$stockinfo = new stockinfo();
		//$stockinfo->where = "stocksymbol = '" . $results['stocksymbol'] . "'";
		//$stockinfo->Select();
		//$result['idstockinfo'] = $stockinfo->resultarray[0]['idstockinfo'];
		$result['idstockinfo'] = $results['idstockinfo'];
		$result['symbol'] = $results['stocksymbol'];
        	$result['marketcap'] = $result['outstandingshare'] * $results['currentprice'];
        	$result['discountrate'] = getdiscountrate( $currentyear );
        	$future = getfuturevalue( $result, $bondratearray );
        	$result['value'] = $future['value'];
        	$result['marginsafety'] = $future['marginsafety'];
		doannualinserts( $result );
	}

/*
	$quarterly = extractquarterly( $filename );
	$qupdate = calculatefinancials( $quarterly );
	$result = calculateratios( $qupdate );

        if( $result != NULL )
	{
		//$stockinfo = new stockinfo();
		//$stockinfo->where = "stocksymbol = '" . $results['stocksymbol'] . "'";
		//$stockinfo->Select();
		//$result['idstockinfo'] = $stockinfo->resultarray[0]['idstockinfo'];
		$result['idstockinfo'] = $results['idstockinfo'];
		$result['symbol'] = $results['stocksymbol'];
        	$result['marketcap'] = $result['outstandingshare'] * $results['currentprice'];
        	$result['discountrate'] = getdiscountrate( $currentyear );
        	$future = getfuturevalue( $result, $bondratearray );
        	$result['value'] = $future['value'];
        	$result['marginsafety'] = $future['marginsafety'];
		doquarterlyinserts( $qupdate );
	}
*/
}

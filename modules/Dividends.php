<?php

/******************************************************************
*
*	Class to find all portfolios that have a given stock
*	on the ex-dividend date, and calculate the appropriate
*	dollar value to put into each persons account
*
******************************************************************/

require_once( 'Dividend/Dividend.class.php' );
require_once( MODELDIR . '/transaction.class.php' );
require_once( MODELDIR . '/transactiontype.class.php' );
require_once( MODELDIR . '/userpref.class.php' );
require_once( MODELDIR . '/users.class.php' );
require_once( MODELDIR . '/dividendpayment.class.php' );

$users = new users();
$userpref = new userpref();
$dividend = new Dividend();
$dividendpayment = new dividendpayment();
$transactions = new transaction();

//Need stocksymbol and stockexchange (from stockinfo) to select the correct stock (idstockinfo) for a user
//Need the ex-dividend date and the dividend amount for the stock
//Need to determine how many shares each user has on the ex-dividend date in each account.
//Calculate the dividend paid to each person per account.
//If the person has ReinvestDividend set TRUE (userpref) add shares instead of dollars.  Add cash for any excess cash.
//	Get the mid price of the day (H + L / 2)
//	DIV (or is it MOD) the dividend -> #shares
//	Add shares, subtract used cash, add leftover cash

/*
	transaction.CalculateSharesAvailableDate
	  transactiondate
	  account
	  username
	  stocksymbol
	Returns #shares
*/

function calcDividends( $stockexchange, $stocksymbol, $exdividenddate, $dividendpershare )
{
}

function insertDividendPayment( $stockexchange, $stocksymbol, $exdividenddate, $dividendpershare )
{
	require_once( MODELDIR . '/dividendpayment.class.php' );
	require_once( MODELDIR . '/stockexchange.class.php' );
	require_once( MODELDIR . '/stockinfo.class.php' );
//Assuming stockexchange is a text string
	$stockexchange = new stockexchange();
	//Need SEARCH code out of controller
	//Assume search performed
	$idstockexchange = $stockexchange->idstockexchange;
	$stockinfo = new stockinfo();
	$stockinfo->idstockexchange = $idstockexchange;
	$stockinfo->stocksymbol = $stocksymbol;
	$stockinfo->GetVARRow();

	$dividendpayment->stocksymbol = $stocksymbol;
	$dividendpayment->dividendpershare = $dividendpershare;
	$dividendpayment->exdividenddate = $exdividenddate;
	$dividendpayment->idstockinfo = $stockinfo->idstockinfo;
	$dividendpayment->idstockexchange = $idstockexchange;
	$dividendpayment->InsertVAR();
}

?>

<?php

//20090804 KF
//Add transactions to the portfolio

function addtransaction( $flog, $username, $symbol, $numbershares, $dollar, $action, $transactiondate, $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )
{
	if( require_once( '../model/transaction.class.php' ))
	{
		$transaction = new transaction();
        	fwrite( $flog, "Created transaction variable.  Adding transaction\n" );
      		$tinsert['username'] = $username;
        	$tinsert['stocksymbol'] = $symbol;
        	$tinsert['numbershares'] = $numbershares;
        	$tinsert['transactiontype'] = $action;
        	$tinsert['dollar'] = $dollar;
		$tinsert['currency'] = $currency;
		$tinsert['foreigncurrency'] = $foreigncurrency;
        	$tinsert['transactiondate'] = $transactiondate;
        	$tinsert['account'] = $account;
        	$tinsert['createdate'] = date( 'Y-m-d h:m:s' );
        	$tinsert['createduser'] = $username;
        	$transaction->Insert( $tinsert );
		return SUCCESS;
	}
	else
		return FAILURE;
}


<?php
//20090804 KF
//Get the mid price for the day
//20120123 KF added to codemeta_functions as part of stockprices class.

function getcloseprice( $flog, $symbol, $transactiondate )
{
	if( require_once( '../model/stockprices.class.php' ))
	{
		fwrite( $flog, "Getting close price for $symbol on $transactiondate\n" );
		$stockprices = new stockprices();
		$stockprices->where = "symbol = '" . $symbol . "' and date = '" . $transactiondate . "'";
		$stockprices->select = "day_close";
		$stockprices->Select();
		//var_dump( $stockprices->resultarray );
		$closeprice = $stockprices->resultarray[0]['day_close'];
		fwrite( $flog, "Close price is $" . $closeprice . "\n" );
		unset( $stockprices );
		return $closeprice;
	}
	else
		return "-1";
}

<?php
//20090804 KF
//Get the mid price for the day
//20120123 KF moved to codemeta_functions 

include_once( '../model/include_all.php' );

function getmidprice( $flog, $symbol, $transactiondate )
{
	if( require_once( '../model/stockprices.class.php' ))
	{
		if( $flog != NULL )
			fwrite( $flog, "Getting mid price for $symbol on $transactiondate\n" );
		$stockprices = new stockprices();
		$stockprices->where = "symbol = '" . $symbol . "' and date = '" . $transactiondate . "'";
		$stockprices->select = "(day_high + day_low) / 2 as midprice";
		$stockprices->Select();
		//var_dump( $stockprices->resultarray );
		$midprice = $stockprices->resultarray[0]['midprice'];
		if( $flog != NULL )
			fwrite( $flog, "Mid price is $" . $midprice . "\n" );
		unset( $stockprices );
		return $midprice;
	}
	else
		return "-1";
}

//TEST
echo getmidprice( NULL, "IBM", "2009-08-07" );

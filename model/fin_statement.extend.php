<?php

//Eventum issue #34 DPS and EPS incorrect in stock info
//20090127 KF 

function UpdateStockinfoDividend( $data = NULL )
{
//20090627 KF
/* This is taken care of by the parse_financials work stream.
	This is probably the better place to do it, but at the moment
	the data doesn't have the idstockinfo, so the insert is failing anyway
*/
	echo "fin_statement.extend.php::UpdateStockinfoDividend\n";
	//return();
	if ($data != NULL)
	{
		//Send the dividend value to the stockinfo table for this stock
		echo "fin_statement.extend.php::UpdateStockinfoDividend data not NULL<br />\n";
		require_once( 'stockinfo.class.php' );
		$s = new stockinfo();
		//var_dump( $data );
		if( !isset( $data['idstockinfo'] ) )
			return;
		if( isset( $data['idstockinfo'] ))
			$update['idstockinfo'] = $data['idstockinfo'];
		if( isset( $data['dividendpershare'] ))
			$update['annualdividendpershare'] = $data['dividendpershare'];
		//#34 added earningpershare field to fin_statement table, parse_financials, and now here to update stockinfo
		if( isset( $data['earningspershare'] ))
			$update['EPS'] = $data['earningspershare'];
		$s->Update( $update );
	}
}


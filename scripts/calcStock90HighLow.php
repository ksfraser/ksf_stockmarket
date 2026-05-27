<?php

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( MODELDIR . '/stockprices.class.php' );
require_once( MODELDIR . '/stockinfo.class.php' );
require_once( MODELDIR . '/stock90highlow.class.php' );

$prices = new stockprices();
$hl = new stock90highlow();
$hl->fieldspec['idstockinfo']['prikey'] = "Y";
//$hl->fieldspec['stocksymbol']['prikey'] = "Y";
$stocks = new stockinfo();

//Get the list of _active_ stocks
$stocks->select = "idstockinfo, stocksymbol, currentprice";
$stocks->where = "active = '1'";
$stocks->Select();

$count = 0;
$found = 0;

foreach( $stocks->resultarray as $row )
{
	if( "CASH" <> $row['stocksymbol'] )
	{
		//$prioes->querystring = "SELECT symbol, date, min(day_low) FROM `stockprices` where symbol = 'AGF-B' group by symbol";
		$prices->select = "symbol, min(day_low) as low";
		//Last 90 days
		$prices->where = "symbol = '" . $row['stocksymbol'] . "' and date > DATE_SUB( CURDATE(), INTERVAL 90 DAY )";
		$prices->groupby = "symbol";
		$prices->Select();
		if( isset(  $prices->resultarray[0] ) )
		{
			$hl->idstockinfo = $row['idstockinfo'];
			$hl->currentprice = $row['currentprice'];
			$hl->stocksymbol = $prices->resultarray[0]['symbol'];
			$hl->low = $prices->resultarray[0]['low'];
			$prices->select = "symbol, max(day_high) as high";
			//retain the 90 days...
			$prices->Select();
			$hl->high = $prices->resultarray[0]['high'];
			$hl->createddate = date( 'Y-m-d h:m:s' );
			$hl->createduser = "system";
			unset( $hl->reviseddate );
			unset( $hl->reviseduser );
			$hl->InsertVAR();
			//echo $hl->querystring . "\n";
			$hl->reviseddate = date( 'Y-m-d h:m:s' );
			$hl->reviseduser = "system";
			unset( $hl->createddate );
			unset( $hl->createduser );
			$hl->UpdateVAR();
			//echo $hl->querystring . "\n";
			echo "Updating for stock $hl->stocksymbol \n";
			$found++;
		}
		else
		{
			echo "No LOW results found for " .  $row['stocksymbol'] . "\n";
			echo $prices->querystring . "\n";  //return ;
			$count++;
		}
	}
}

echo "Failed to find data for $count stocks\n";
echo "updated $found stocks\n";

?>

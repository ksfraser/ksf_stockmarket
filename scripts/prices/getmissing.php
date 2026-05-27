<?php

/********************************
*
*	This function is to 
*	query YAHOO for any
*	stocks that we don't
*	have in the stockprices
*	database.  Using 
*	queryyahoo-all, we will
*	download every last days
*	data for the stock.
*
********************************/

require_once( '../../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );

//include( $MODELDIR . '/stockprices.class.php' );
include( $MODELDIR . '/stockinfo.class.php' );
//include( $MODELDIR . '/stockexchange.class.php' );
//include( 'view/class.genericpage.php' );
//require_once( $MODELDIR . '/tradedates.class.php' );
require_once( '../common/cleanstockprices.php' );
//require_once( '../common/webpage2txt.php' );
require_once( '../common/yahooexchanges.php' );
//require_once( 'extractinsert.php' );
require_once( 'queryyahoo-all.php' );

//Define some constants
$const_YEAR = "1970";
$const_MONTH = "1";
$const_DAY = "01";

function getmissing( $flog, $thisex )
{
	/*20090705 KF
	*The following logic grabs all symbols not currently
	*in the stockprices database and then adds them
	*/
global $const_YEAR;
global $const_MONTH;
global $const_DAY;
	fwrite( $flog, "\n\nSTARTING download of missing data\n" );
	$stock = new stockinfo();
	$stock->where = "stocksymbol not in (select symbol from stockprices)";
	$stock->Select();
	foreach( $stock->resultarray as $key => $value )
	{
		$symbol = $value['stocksymbol'];
		$idstockinfo = $value['idstockinfo'];
		fwrite( $flog, "Symbol " . $symbol . " Not in the database.  Asking Yahoo for data.\n");
		if( 
			( $symbol != 'CASH' )
			AND ( $symbol != 'BOO' )
			AND ( $symbol != 'ZZZ' )
		)
		{
			$filename = queryyahoo_all( $symbol, $thisex[ $value['stockexchange'] ] 
						,$const_YEAR, date( 'Y' ), 
						$const_MONTH, date( 'm' ), 
						$const_DAY, date( 'd' ),
						$flog
						);
			//extractinsert( $flog, $filename, $symbol, $value );
		}
	}
	unset( $stock );
	return SUCCESS;
}





/*20090801 KF
* Add a logfile to the prog
*/
$flog = fopen( $APPDIR . "/logs/getmissing" . date( 'Ymdhs' ) . ".txt", "w" );
fwrite( $flog, "Started run" );

$thisex = yahooexchanges();
getmissing( $flog, $thisex );
fclose( $flog );
?>

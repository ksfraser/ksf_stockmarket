<?php
echo __FILE__;

require_once( '../local.php' );
require_once( 'data/generictable.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
include_once( $MODELDIR . '/stockprices.class.php' );
include_once( $MODELDIR . '/stockinfo.class.php' );
include_once( $MODELDIR . '/stockexchange.class.php' );
include_once( 'view/class.genericpage.php' );
require_once( $MODELDIR . '/tradedates.class.php' );
require_once( 'common/cleanstockprices.php' );
require_once( 'common/webpage2txt.php' );
require_once( 'common/yahooexchanges.php' );

//Define some constants
$const_YEAR = "1970";
$const_MONTH = "1";
$const_DAY = "01";

function extractinsert( $flog,  $filename = NULL, $symbol, $value )
{
	//return;
	if( NULL == $filename )
	{
		fwrite( $flog, "No file to extract data from\n" );
		return FAILURE;
	}
	else
	if( NULL == $symbol )
	{
		fwrite( $flog, "No symbol to wrtie data for\n" );
		return FAILURE;
	}
	else
	if( NULL == $value )
	{
		fwrite( $flog, "No idstockinfo to write data for\n" );
		return FAILURE;
	}
	else
	{
		$fp = fopen( $filename, "r" );
		if( NULL == $fp )
		{
			fwrite( $flog, "Can't open data file $filename\n" );
			return FAILURE;
		}
		$stockprices = new stockprices();
		$tradedates = new tradedates();
		while( !feof( $fp ))
		{
			$fields = fgetcsv( $fp, 1024 );
			/* Yahoo CSV format:
			*Date,
			*Open,
			*High,
			*Low,
			*Close,
			*Volume,
			*Adj Close
			*/
			$insert['date'] = $fields[0];
			$insert['day_open'] = $fields[1]; 
			$insert['day_high'] = $fields[2]; 
			$insert['day_low'] = $fields[3]; 
			$insert['day_close'] = $fields[4]; 
			$insert['volume'] = $fields[5]; 
			$insert['adjustedclose'] = $fields[6]; 
			$insert['symbol'] = $symbol;
			$insert['idstockinfo'] = $value['idstockinfo'];
			if( $insert['date'] != NULL )
			{
				$stockprices->UpdateInsert( $insert );
				unset($stockprices->log);
				unset($stockprices->errors);
				$insert['tradedates'] = $insert['date'];
				$tradedates->Insert( $insert );
				unset($tradedates->log);
				unset($tradedates->errors);
			}
			unset( $insert );
			unset( $fields );
		}
		unset($stockprices);
		unset($tradedates);
		fclose( $fp );
		return SUCCESS;
	}
}





/*20090801 KF
* Add a logfile to the prog

*/
$flog = fopen( "../logs/yahoo-insert2stockprices" . date( 'Ymdhs' ) . ".txt", "w" );
fwrite( $flog, "Started run" );

$stockexchange = new stockexchange();

$thisex = yahooexchanges();



	$const_YEAR1 = "1970";
	$const_YEAR2 = "2013";
	$const_MONTH1 = "0";
	$const_MONTH2 = "10";
	$const_DAY1 = "01";
	$const_DAY2 = "17";

        $stock = new stockinfo();
        //$stock->where = "stocksymbol not in (select symbol from stockprices)";
        $stock->Select();
        foreach( $stock->resultarray as $key => $value )
        {
                $symbol = $value['stocksymbol'];
                $idstockinfo = $value['idstockinfo'];
                if(
                        ( $symbol != 'CASH' )
                        AND ( $symbol != 'BOO' )
                        AND ( $symbol != 'ZZZ' )
                )
                {
			//../currentdata/ZSMMF.TO.1970001-20131017.csv
                        $filename = "../currentdata/" . $symbol . "." . $thisex[$value['stockexchange']] . "." . $const_YEAR1 . $const_MONTH1 . $const_DAY1 . "-" . $const_YEAR2 . $const_MONTH2 . $const_DAY2 . ".csv";
                                                ;
                        extractinsert( $flog, $filename, $symbol, $value );
                }
	}



fclose( $flog );
?>

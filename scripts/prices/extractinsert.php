<?php

require_once( 'data/generictable.php' );
require_once( $MODELDIR . '/stockprices.class.php' );
require_once( $MODELDIR . '/tradedates.class.php' );


function extractinsert( $flog,  $filename = NULL, $symbol, $value )
{
	return;
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

?>

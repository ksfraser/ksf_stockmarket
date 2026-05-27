<?php

global $APPDIR;

require_once( $APPDIR . '/scripts/common/webpage2txt.php' );

function queryyahoo_all( $stock, $stockexchange = "" 
	,$STARTYEAR='2010', $ENDYEAR='2010', 
	$STARTMONTH='0', $ENDMONTH= '11', 
	$STARTDAY='01', $ENDDAY= '21',
	$flog = NULL
	)
{
global $APPDIR;
//This function will query a stock for ALL its data.
	if( strlen($stockexchange) > 0) 
	{
		$symbol = $stock . "." . $stockexchange;
	}
	else
	{
		$symbol = $stock;
	}
	$query = "http://ichart.finance.yahoo.com/table.csv?s=" 
		. $symbol 
		. "&amp;a=" . ($STARTMONTH - 1) 
		. "&amp;b=" . ($STARTDAY + 1) 
		. "&amp;d=" . $ENDMONTH 
		. "&amp;e=" . $ENDDAY 
		. "&amp;f=" . $ENDYEAR;
echo "All query: " . $query . "\n";
	fwrite( $flog, "URL:  $query\n" );
	$text = webpage2txt( $query );
	$filename = $APPDIR . "/currentdata/prices/" . $symbol . "." . $STARTYEAR . $STARTMONTH . $STARTDAY . "-" . $ENDYEAR . $ENDMONTH . $ENDDAY .  ".csv";
	fwrite( $flog, "Data file:  $filename\n\n" );
	$fp = fopen( $filename, "w" );
	if( NULL == $fp )
	{
		fwrite( $flog, "couldn't create $filename\n" );
		$filename = NULL;
	}
	else
	{
		fwrite( $fp, $text );
		fclose ( $fp );
		$len = strlen( $text );
		fwrite( $flog, "Wrote " . $len . " characters\n" );
		if( $len == 0 )
			$filename = NULL;
	}
	unset( $text );
	return $filename;
}

?>

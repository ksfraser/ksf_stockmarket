<?php

global $APPDIR;

require_once( $APPDIR . '/scripts/common/webpage2txt.php' );

function QueryYahoo( $stock, $stockexchange = "" 
	,$STARTYEAR='2000', $ENDYEAR='2009', 
	$STARTMONTH='0', $ENDMONTH= '11', 
	$STARTDAY='01', $ENDDAY= '31',
	$flog = NULL
	)
{
global $APPDIR;
//This function queries for a stock's data within the date range

	if( $STARTYEAR == $ENDYEAR and $STARTMONTH == $ENDMONTH and $STARTDAY == $ENDDAY )
	{
		fwrite( $flog, "Stock $stock has reached the end of the date limits\n" );
		return NULL;
	}
	if( strlen($stockexchange) > 0) 
	{
		$symbol = $stock . "." . $stockexchange;
	}
	else
	{
		$symbol = $stock;
	}
	//The following can all be set to change the parameters
	$query = "http://ichart.finance.yahoo.com/table.csv?s=" 
		. $symbol 
		. "&a=" . ($STARTMONTH - 1) 
		. "&b=" . ($STARTDAY + 1) 
		. "&c=" . $STARTYEAR 
		. "&d=" . $ENDMONTH 
		. "&e=" . $ENDDAY 
		. "&f=" . $ENDYEAR 
		. "&g=d"
		. "&ignore=.csv";
echo "Query: " . $query . "\n";
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

	//$query = "http://ichart.finance.yahoo.com/table.csv?s=" . $symbol . "&amp;a=" . $STARTMONTH . "&amp;b=" . $STARTDAY . "&amp;d=" . $ENDMONTH . "&amp;e=" . $ENDDAY . "&amp;f=" . $ENDYEAR;

?>

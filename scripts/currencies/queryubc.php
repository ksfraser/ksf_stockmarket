<?php

/**********************************************************************
*
*	20110807 KF Startmonth is now 1-12 rather than 0-11
*
************************************************************************/

require_once( '../common/webpage2txt.php' );
require_once( '../common/monthmaxday.php' );

function QueryUBC( $currency = "CAD", $foreigncurrency = "USD", $STARTYEAR='1990', $ENDYEAR='2009', 
	$STARTMONTH='1', $ENDMONTH= '07', $STARTDAY='01', $ENDDAY= '01' )
{
	$STARTDAY = monthmaxday( $STARTMONTH, $STARTDAY );
	$ENDDAY = monthmaxday( $ENDMONTH, $ENDDAY );

	$query = "http://fx.sauder.ubc.ca/cgi/fxdata?b=" . $currency . "&ld=" . $ENDDAY . "&lm=" . $ENDMONTH . "&ly=" . $ENDYEAR . "&fd=" . $STARTDAY . "&fm=" . $STARTMONTH . "&fy=" . $STARTYEAR . "&daily&q=volume&f=csv&o=T.C&c=" . $foreigncurrency;
	echo $query . "\n";
	$text = webpage2txt( $query );
	$filename = BASEDIR . "/currentdata/currencies/" . $currency . "-" . $foreigncurrency . "." . $STARTYEAR . $STARTMONTH . "-" . $ENDYEAR . $ENDMONTH . ".csv";
	$fp = fopen( $filename, "w" );
	fwrite( $fp, $text );
	fclose ( $fp );
	return $filename;
}

?>

<?php

//Cash Flow
//http://ca.finance.yahoo.com/q/cf?s=CP&annual
//Balance Sheet
//http://ca.finance.yahoo.com/q/bs?s=CP&annual
//Incomes Statement
//http://ca.finance.yahoo.com/q/is?s=CP&annual

require_once( 'data/webpage2text.php' );
require_once( 'data/downloadpage.php' );
require_once( 'yahoo-findata2xml.php' );

function yahoostatements( $symbol )
{
	$date = date( 'Ymd' );
	$query = "http://ca.finance.yahoo.com/q/is?s=" . $symbol . "&annual";
	$text = downloadpage( $query );
        $filename = "data/" . $symbol . ".income." . $date . ".html";
        $fp = fopen( $filename, "w" );
        fwrite( $fp, $text );
        fclose ( $fp );
	$incomexml = findata2xml( $filename );

	$query = "http://ca.finance.yahoo.com/q/bs?s=" . $symbol . "&annual";
	$text = downloadpage( $query );
        $filename = "data/" . $symbol . ".balance." . $date . ".html";
        //fwrite( $flog, "Data file:  $filename\n\n" );
        $fp = fopen( $filename, "w" );
        fwrite( $fp, $text );
        fclose ( $fp );
	$balancexml = findata2xml( $filename );

	$query = "http://ca.finance.yahoo.com/q/cf?s=" . $symbol . "&annual";
	$text = downloadpage( $query );
        $filename = "data/" . $symbol . ".cashflow." . $date . ".html";
        //fwrite( $flog, "Data file:  $filename\n\n" );
        $fp = fopen( $filename, "w" );
        fwrite( $fp, $text );
        fclose ( $fp );
	$cashflowxml = findata2xml( $filename );

	$xmlstring = $incomexml . $balancexml . $cashflowxml;
        $filename = "data/" . $symbol . ".combinedxml." . $date . ".html";
        $fp = fopen( $filename, "w" );
        fwrite( $fp, $xmlstring );
        fclose ( $fp );

	return $xmlstring;
}

//TEST
$xmlstring = yahoostatements( "CP" );
echo $xmlstring . "\n";


?>

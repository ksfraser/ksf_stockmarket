<?php

//http://www.bankofcanada.ca/rates/interest-rates/canadian-bonds/


function getbondrates()
{

	global $APPDIR;
//20110123 KF on the 21st www.b... worked, whereas today the URL is www1....	
	$url = "http://www1.bankofcanada.ca/en/rates/bonds.html";
	//echo "URL: $url \n";
	//sleep(1);
	$fp = fopen( $url, "r" );
	
	if( $fp )
	{
	        $data = "";
	        while (!feof($fp)) {
	                    $data .= @fread($fp, 1024);
	        }
	        fclose($fp);
		$filename = $APPDIR . "/currentdata/bond/" . date( 'Ymd' ) . ".html";
	        $fp2 = fopen( $filename, "w" );
	        fwrite( $fp2, $data );
	        fclose( $fp2 );
	}
	else
	{
		echo "URL OPEN FAILED";
		EmailAlert( "kevin", "Bond Update Failed", "Bond update failed on opening the URL $url\n" );
		exit(0);
	}
	
	//Parse the page for bond info
	
	$chunks = preg_split( "/<table/i", $data, -1, PREG_SPLIT_OFFSET_CAPTURE );
	/* Long Term Rate array */
	$year = date( "Y" );
		//echo $year . "\n";
	//chunk 1 tells year range
	//chunk 2 is years 1-3 rates
		//var_dump( $chunks[2] );
		$rowarray = preg_split( '/<tr/i', $chunks[2][0] );
		//var_dump( $rowarray );
		$ratearray = preg_split( '/(<b>|<\/b>)/i', $rowarray[6] );
		//var_dump( $ratearray );
		$rate[ (string)($year + 1) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 2) . '-01-01' ] = (float)$ratearray[1];
	//chunk 3 is years 3-5 rates
		//var_dump( $chunks[3] );
		$rowarray = preg_split( '/<tr/i', $chunks[3][0] );
		//var_dump( $rowarray );
		$ratearray = preg_split( '/(<b>|<\/b>)/i', $rowarray[6] );
		//var_dump( $ratearray );
		$rate[ (string)($year + 3) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 4) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 5) . '-01-01' ] = (float)$ratearray[1];
	//chunk 4 is years 6-10 rates
		//var_dump( $chunks[4] );
		$rowarray = preg_split( '/<tr/i', $chunks[4][0] );
		//var_dump( $rowarray );
		$ratearray = preg_split( '/(<b>|<\/b>)/i', $rowarray[6] );
		//var_dump( $ratearray );
		$rate[ (string)($year + 6) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 7) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 8) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 9) . '-01-01' ] = (float)$ratearray[1];
		$rate[ (string)($year + 10) . '-01-01' ] = (float)$ratearray[1];
	
		//var_dump( $chunks[5][0] );
		$longchunk = $chunks[5][0];
		$longrows = preg_split( "/<tr/i", $longchunk );
		//var_dump( $longrows );
		//var_dump( $longrows[6] );
		$longratearray = preg_split( '/(<b>|<\/b>)/i', $longrows[6] );
		//var_dump( $longratearray );
		//$rate['30year'] = (float)$longratearray[1];
		$rate[ (string)($year + 30) . '-01-01' ] = (float)$longratearray[1];
		echo "Dumping Rates";
		var_dump( $rate );
	
	return $rate;
}

//TEST
// var_dump( getbondrates() );

require_once( '../include_all.php' );
require_once( $MODELDIR . '/bondrate.class.php' );
$bondrates = new bondrate();
$bondrates->Select();
$rates = getbondrates();
if( count( $rates ) < 10 )
	EmailAlert( "kevin", "Bond Update WARNING", "Bond update has less than 10 rates returned.  In the past 11 were normal.  Please investigate\n" );

foreach( $bondrates->resultarray as $row )
{
	$update['idbondrate'] = $row['idbondrate'];
	$update['calendaryear'] = $row['calendaryear'];
	if( isset( $rates[$row['calendaryear']] ))
	{
		$update['bondrate'] = $rates[$row['calendaryear']];
		$bondrates->Update( $update );
		unset( $rates[$row['calendaryear']] );
	}
	else
	{
		//No rate data to update the year with
	}
}
//At this point $rates contains data that didn't already
//exist in the table, so we want to add.
	var_dump( $rates );
	foreach( $rates as $year=>$value )
	{
		$insert['calendaryear'] = $year;
		$insert['bondrate'] = $value;
		$bondrates->Insert( $insert );
	}


?>

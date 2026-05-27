<?

function findata2xml( $filename )
{
	$fp = fopen( $filename, "r" );
	$data = fread( $fp, 100000 );
	fclose( $fp );
	require_once( 'data/tableextractor.php' );
	$tbl = new tableExtractor;
	$tbl->source = $data; // Set the HTML Document
	$tbl->anchor = 'Annual Data'; // Set an anchor that is unique and occurs before the Table
	$tpl->anchorWithin = true; // To use a unique anchor within the table to be retrieved
	$d = $tbl->extractTable(); // The array
	//var_dump( $d );
	
	require_once( 'data/xml.php' );
	$xml = new xml();
	
	$bad =  array( "-", "(", ")", "&nbsp;", "$", "<b>", "</b>" );
	$good = array( "0", "-", "",  "",       "",  "",    ""     );
	$badstr =  array( "(", ")", "&nbsp;", "$", "<b>", "</b>", "<small>", "</small>" );
	$goodstr = array( "-", "",  "",       "",  "",    "",     "",        ""         );
	
	$line = "";
	//$year0 = "This Year";
	//$year1 = "Last Year";
	//$year2 = "Two Years ago";
	foreach( $d as $arr )
	{
		$data = array();
		if( count( $arr ) == 5 )
		{
			$arr[1] = str_replace( $badstr, $goodstr, $arr[1]);
			$arr[2] = str_replace( $badstr, $goodstr, $arr[2]);
			$arr[3] = str_replace( $badstr, $goodstr, $arr[3]);
			$arr[4] = str_replace( $badstr, $goodstr, $arr[4]);
			$arr[5] = str_replace( $badstr, $goodstr, $arr[5]);
			//var_dump( $arr );
			if( $arr[2] == "PERIODENDING" )
			{
				$year0 = $arr[3];
				$year1 = $arr[4];
				$year2 = $arr[5];
				$data[0] = $year0;
				$data[1] = $year1;
				$data[2] = $year2;
				$name = "PeriodEndDates";
				$line .= $xml->Array2XML( $data, $name );
			}
		}
		if( count( $arr ) == 4 )
		{
			//var_dump( $arr );
		
			$name = str_replace( $bad, $good, $arr[1]);
			$data[0] =  str_replace( $bad, $good, $arr[2]);
			$data[1] =  str_replace( $bad, $good, $arr[3]);
			$data[2] =  str_replace( $bad, $good, $arr[4]);
			//3 years of data plus header cell
			$line .= $xml->Array2XML( $data, $name );
		}
	}
	return $line;
}

//TEST
/*
$line = findata2xml( "CP.html" );
echo $line . "\n";
*/

?>

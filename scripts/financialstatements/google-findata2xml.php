<?

function findata2xml( $filename, $anchor )
{
	$fp = fopen( $filename, "r" );
	$data = fread( $fp, 1000000 );
	fclose( $fp );
	require_once( 'data/tableextractor.php' );
	$tbl = new tableExtractor;
	$tbl->source = $data; // Set the HTML Document
	$tbl->anchor = 'annualdiv'; // Set an anchor that is unique and occurs before the Table
	$tpl->anchorWithin = true; // To use a unique anchor within the table to be retrieved
	$d = $tbl->extractTable(); // The array
	//var_dump( $d );
	
	require_once( 'data/xml.php' );
	$xml = new xml();
	
	$bad =  array( "-", "(", ")",  "$", "<b>", "</b>", "12monthsending", "(exceptforpershareitems)", "/", ",", "&",   "<spanclass=chr>", "<span>" );
	$good = array( "0", "",  "",   "",  "",    "",     "",               "",                         "",  "",  "And", "",                "" );
	$badstr =  array( "(", ")", "&nbsp;", "$", "<b>", "</b>", "<small>", "</small>" );
	$goodstr = array( "-", "",  "",       "",  "",    "",     "",        ""         );
	
	$line = "";
	//$year0 = "This Year";
	//$year1 = "Last Year";
	//$year2 = "Two Years ago";
	foreach( $d as $arr )
	{
		$data = array();
		//var_dump( $arr );
		if( count( $arr ) == 5 )
		{
			$icount = 1;
			foreach( $arr as $key => $value )
			{
				if( $icount == 1 )
				{
					$name = str_replace( $bad, $good, $value);
					$units[ "t0" ] = $key;
				}
				else
				{
					if( $icount == 2 )
					{
						$tag = "t0";
					}
					else
					if( $icount == 3 )
					{
						$tag = "t1";
					}
					else
					if( $icount == 4 )
					{
						$tag = "t2";
					}
					else
					if( $icount == 5 )
					{
						$tag = "t3";
					}
					$data[ $tag ] =  str_replace( $bad, $good, $value);
					$reportingdate[ $tag ] =  $key;
				}
				$icount++;
			}
			//var_dump( $arr );
			$line .= $xml->Array2XML( $data, $name );
		}
	}
	$line .= $xml->Array2XML( $reportingdate, "Dates" );
	$line .= $xml->Array2XML( $units, "Units" );
	//$line = str_replace( '\n', '\t', $line );
	return $line;
}

/*
//TEST
$line = findata2xml( "../../fin_reports/CEO.stock.html", "incinterimdiv" );
echo $line . "\n";
$quarterly = $line;
$line = findata2xml( "../../fin_reports/CEO.stock.html", "balinterimdiv" );
echo $line . "\n";
$quarterly .= $line;
$line = findata2xml( "../../fin_reports/CEO.stock.html",  "casinterimdiv");
echo $line . "\n";
$quarterly .= $line;
$line = findata2xml( "../../fin_reports/CEO.stock.html", "incannualdiv" );
echo $line . "\n";
$annual = $line;
$line = findata2xml( "../../fin_reports/CEO.stock.html", "balannualdiv" );
echo $line . "\n";
$annual .= $line;
$line = findata2xml( "../../fin_reports/CEO.stock.html", "casannualdiv" );
echo $line . "\n";
$annual .= $line;
*/
?>

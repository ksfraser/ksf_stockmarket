<?php
echo __FILE__;

function webpage2txt($url)
{
	$user_agent = "Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)";
	$ch = curl_init();    // initialize curl handle
	curl_setopt($ch, CURLOPT_URL, $url); // set url to post to
	curl_setopt($ch, CURLOPT_FAILONERROR, 1);              // Fail on errors
	curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);    // allow redirects
	curl_setopt($ch, CURLOPT_RETURNTRANSFER,1); // return into a variable
	curl_setopt($ch, CURLOPT_PORT, 80);            //Set the port number
	curl_setopt($ch, CURLOPT_TIMEOUT, 15); // times out after 15s
	curl_setopt($ch, CURLOPT_USERAGENT, $user_agent);
	$document = curl_exec($ch);

	$search = array('@<script[^>]*?>.*?</script>@si',  // Strip out javascript
		'@<style[^>]*?>.*?</style>@siU',    // Strip style tags properly
		'@<[\/\!]*?[^<>]*?>@si',            // Strip out HTML tags
		'@<![\s\S]*?.[ \t\n\r]*>@',         // Strip multi-line comments including CDATA
		'/\s{2,}/',
		);

	$text = preg_replace($search, "\n", html_entity_decode($document));

	$pat[0] = "/^\s+/";
	$pat[2] = "/\s+\$/";
	$rep[0] = "";
	$rep[2] = " ";
	$text = preg_replace($pat, $rep, trim($text));
	return $text;
}

function QueryDividends( $stocklist )
{

	$query = "http://ca.finance.yahoo.com/d/quotes.csv?f=r1qder&s=" . $stocklist;


	echo $query . "\n";
	$text = webpage2txt( $query );
	$filename = "../currentdata/dividend-dates.csv";
	$fp = fopen( $filename, "w" );
	fwrite( $fp, $text );
	fclose ( $fp );
	return $filename;
}

require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
include( $MODELDIR . '/stockinfo.class.php' );
$stockinfo = new stockinfo();
include( 'view/class.genericpage.php' );
$page = new genericpage();
$page->mode = "search";
$menu = $Security->AddMenu();
$page->SetItem( $menu );

$stockinfo->select = "stocksymbol, stockexchange";
$stockinfo->Select();

$count = 0;
$stocklist = "";

foreach( $stockinfo->resultarray as $row )
{
	if( $count > 0 )
		$stocklist .= "+";
	$stocklist .= $row['stocksymbol'];
	$count++;
	$stocks[] = $row['stocksymbol'];
}

	$filename = QueryDividends( $stocklist );
	echo $filename;
/*
	$fp = fopen( $filename, "r" );
	while( !feof( $fp ))
	{
		$fields = fgetcsv( $fp, 1024 );
			$insert['date'] = $fields[1];
			$insert['day_close'] = $fields[3]; 
			$insert['currency'] = $currency;
			$insert['foreigncurrency'] = $foreigncurrency;
		//	if( $insert['date'] != NULL )
		//		$stockinfo->Insert( $insert );
	}
*/


?>

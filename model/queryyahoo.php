<?php

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

function parse_line($input_text, $delimiter = ',', $text_qualifier = '"') {
    $text = trim($input_text);
    
    if(is_string($delimiter) && is_string($text_qualifier)) {
        $re_d = '\x' . dechex(ord($delimiter));            //format for regexp
        $re_tq = '\x' . dechex(ord($text_qualifier));    //format for regexp
    
        $fields = array();
        $field_num = 0;
        while(strlen($text) > 0) {
            if($text{0} == $text_qualifier) {
                preg_match('/^' . $re_tq . '((?:[^' . $re_tq . ']|(?<=\x5c)' . $re_tq . ')*)' . $re_tq . $re_d . '?(.*)$/', $text, $matches);
                
                $value = str_replace('\\' . $text_qualifier, $text_qualifier, $matches[1]);
                $text = trim($matches[2]);
                
                $fields[$field_num++] = $value;
            } else {
                preg_match('/^([^' . $re_d . ']*)' . $re_d . '?(.*)$/', $text, $matches);
                
                $value = $matches[1];
                $text = trim($matches[2]);
                
                $fields[$field_num++] = $value;
            }
        }
    
        return $fields;
    } else {
        return false;
    }
}


function QueryYahoo( $stock, $stockexchange = "" )
{

//$query = "http://finance.yahoo.com/d/quotes.csv?s=CP.TO&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";
//$query = "http://finance.yahoo.com/d/quotes.csv?s=CNR.TO&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";

if( strlen($stockexchange) > 0) 
{
	$symbol = $stock . "." . $stockexchange;
}
else
{
	$symbol = $stock;
}

$query = "http://finance.yahoo.com/d/quotes.csv?s=" . $symbol . "&f=sl1d1t1c1ohgva2pm3m4bb6aa5&e=.csv";
echo $query . "\n";

$text = webpage2txt( $query );
//echo $text;
$fp = fopen( "../currentdata/" . $symbol . ".html", "w" );
fwrite( $fp, $text );
fclose ( $fp );
$fields = parse_line( $text );
//var_dump( $fields );

/* Yahoo CSV format:
*
*	Symbol, 
*	last trade, 
*	trade date, 
*	trade time, 
*	change, 
*	open, 
*	high, 
*	low, 
*	volume,
*	average volume, 
*	prev close, 
*	after hours price, 
*	unknown, 
*	bid, 
*	bidsize, 
*	ask, 
*	asksize
*
*/

$stockarray['symbol'] = $fields[0];
$stockarray['last trade'] = $fields[1]; 
$stockarray['trade date'] = $fields[2]; 
$stockarray['trade time'] = $fields[3]; 
$stockarray['dailychange'] = $fields[4]; 
$stockarray['open'] = $fields[5]; 
$stockarray['high'] = $fields[6]; 
$stockarray['low'] = $fields[7]; 
$stockarray['volume'] = $fields[8];
$stockarray['average volume'] = $fields[9]; 
$stockarray['prev close'] = $fields[10]; 
$stockarray['after hours price'] = $fields[11]; 
$stockarray['oneyeartarget'] = $fields[12]; 
$stockarray['bid'] = $fields[13]; 
$stockarray['bidsize'] = $fields[14]; 
$stockarray['ask'] = $fields[15]; 
$stockarray['asksize'] = $fields[16];

//var_dump( $stockarray );
return $stockarray;

}

function ResultsToInsert( $stock, $results )
{
//var_dump( $stock );
//echo "<br />" . $stock->resultarray[0][0];
//echo "<br />";
	$return['stocksymbol'] = $stock['stocksymbol'];
	$return['averagevolume'] = $results['average volume'] ;
	$return['low'] = $results['low'] ;
	$return['high'] = $results['high'] ;
	$return['currentprice'] = $results['last trade'] ;
	$return['dailyvolume'] = $results['volume'];
	if ($results['high'] > $stock['yearhigh'])
		$return['yearhigh'] = $results['high'];
	if ($results['low'] < $stock['yearlow'])
		$return['yearlow'] = $results['low'];

	return $return;
}

require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
include( 'stockinfo.class.php' );
$stock = new stockinfo();
include( 'stockexchange.class.php' );
$stockexchange = new stockexchange();
include( 'view/class.genericpage.php' );
$page = new genericpage();
$page->mode = "search";
$menu = $Security->AddMenu();
$page->SetItem( $menu );
$stock->Select();
$stockexchange->Select();
	foreach( $stockexchange->resultarray as $key => $evalue )
	{
		$thisex[ $evalue['idstockexchange'] ] = $evalue['YahooSymbol'];
	}
	//var_dump( $thisex );
foreach( $stock->resultarray as $key => $value )
{
	$symbol = $value['stocksymbol'];
	if ( $symbol != 'CASH' )
	{
		$result = QueryYahoo( $symbol, $thisex[ $value['stockexchange'] ] );
		$insert = ResultsToInsert( $value, $result );
		$insert['idstockinfo'] = $value['idstockinfo'];
		$stocksymbol->fieldspec[$symbol]['prikey'] = 'Y';
		$stock->Update( $insert );
	}
}
//This shows the stockinfo page.
/*
$page->PageAddTable( $stock );
$page->SetItem($page->Array2Table( $result ) );
$page->Display();
*/
?>

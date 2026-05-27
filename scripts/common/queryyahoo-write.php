<?php

function QueryYahooWrite( $stock, $stockexchange = "" )
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
//echo $query . "\n";

$text = webpage2txt( $query );
//echo $text;
$fp = fopen( "../currentdata/" . $symbol . ".html", "w" );
fwrite( $fp, $text );
fclose ( $fp );

return $text;
}

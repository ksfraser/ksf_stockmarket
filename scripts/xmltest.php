<?php

require_once( 'data/xml.php' );

$xml = new xml();

$string = "<html><body><h1>test</h1><h2>Another test</h2></body></html>";
$array[] = "html";
$array[] = "body";
$array[] = "h1";
$array[] = "h2";


$xml->XML2Array( $string, $array );

var_dump( $xml->results );

?>

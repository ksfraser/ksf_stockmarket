<?php

$fp = fopen( 'CP.html', 'r' );
$simple = fread( $fp, 100000 );

//$simple = "<para><note>simple note</note></para>";
$p = xml_parser_create();
xml_parse_into_struct($p, $simple, $vals, $index);
xml_parser_free($p);
echo "Index array\n";
var_dump($index);
echo "\nVals array\n";
var_dump($vals);
?>

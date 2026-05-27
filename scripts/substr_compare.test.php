<?php

$val="1.234B";
$vlen = strlen( $val );
$cmpstr = "B";
$res = substr_compare( $val, $cmpstr, $vlen -1, 1, false );
echo "Val $val of length $vlen has compare against $cmpstr result of $res\n";
?>

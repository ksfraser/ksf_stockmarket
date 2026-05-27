<?php

echo "This file is named $argv[0]\n";
$fp = fopen( "test.txt", "w" );
fwrite( $fp, date( "Y-m-d H:i:s" ) . " This file is named $argv[0]\n" );
fclose( $fp );
?>

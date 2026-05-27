<?php
require_once( '../model/include_all.php' );
require_once( 'account-transactions.php' );
$result = CalculateDollarsAvailable( "candlestick-simple-IBM", "CASH" );
echo "Result is $result\n";
$result = CalculateSharesAvailable( "kevin", "CASH" );
echo "Result is $result\n";
$result = CalculateSharesAvailable( "kevin", "IBM" );
echo "Result is $result\n";

?>

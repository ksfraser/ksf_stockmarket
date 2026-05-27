<?php
require_once( 'buyhold.class.php' );

        //go through technical analysis for this symbol,
        //using the identified buyholds sell or buy
        //ALL stocks or all cash.
        //
        //DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
                $user = "buyhold";
                $firstname = "Buy";
                $lastname = "Hold";
                $email = "fraser.ks@gmail.com";
                $currency = "CAD";
                $foreigncurrency = "CAD";
                $account = "TRADE";
        $buyhold = new buyhold( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $buyhold->AddUser( $firstname, $lastname, $email );
        $buyhold->RunStrategy();


?>

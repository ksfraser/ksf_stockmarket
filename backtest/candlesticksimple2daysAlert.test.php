<?php
require_once( 'candlesticksimple2daysAlert.class.php' );

        //go through technical analysis for this symbol,
        //using the identified candlesticks sell or buy
        //ALL stocks or all cash.
        //
        //DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
                $user = "cs_2daysAlert";
                $firstname = "Candlestick";
                $lastname = "Simple2daysAlert";
                $email = "fraser.ks@gmail.com";
                $currency = "CAD";
                $foreigncurrency = "CAD";
                $account = "TRADE";
        $candlesticksimple2daysAlert = new candlesticksimple2daysAlert( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2daysAlert->AddUser( $firstname, $lastname, $email );
        $candlesticksimple2daysAlert->RunStrategy();
	exit();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple2daysAlert2 = new candlesticksimple2daysAlert( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2daysAlert2->AddUser( $firstname, $lastname, $email );
	$candlesticksimple2daysAlert2->Setbuystockaverage( "55" );
	$candlesticksimple2daysAlert2->Setsellstockaverage( "45" );
        $candlesticksimple2daysAlert2->RunStrategy();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple2daysAlert3 = new candlesticksimple2daysAlert( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2daysAlert3->AddUser( $firstname, $lastname, $email );
	$candlesticksimple2daysAlert3->Setbuystockaverage( "65" );
	$candlesticksimple2daysAlert3->Setsellstockaverage( "35" );
        $candlesticksimple2daysAlert3->RunStrategy();

?>

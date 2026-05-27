<?php

/*
http://www.greenfaucet.com/technical-analysis/big-gains-come-from-buying-leading-stocks-at-support/01326

While the indexes continue to show range-bound trade, stocks like ROVI, NFLX and AAPL are showing us it's a market of stocks.

And to make the most of your trading, all you need to know is:

Support, Resistance, The 50 day and Trend Channel Support and Resistance. There is no need to make it any harder than it needs to be. Below is the 60 minute chart of the S&P 500

Those that understand how to buy support and are prepared to do so, got paid nicely today in ROVI. Notice where the lows were this morning. Why?

Because that is a support level. We've had that blue line on this chart long before this issue even got anywhere near it today. Just another reason why you need to use and know what support and resistance is all about.

*/


echo __FILE__ . "\n";
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
require_once( 'strategiesConstants.php' );

require_once( MODELDIR . '/technicalanalysis.class.php' );
$ta = new technicalanalysis();



?>

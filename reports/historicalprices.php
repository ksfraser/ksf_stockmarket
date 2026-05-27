<?php

//20090718 KF Display a graph historical prices for a stock.

//OPTIONS
//Show 1 or more stocks
//Choose:
//	Candlestick (1 stock only)
//	Opening prices
//	Closing prices
//	Daily High
//	Daily Low
//	Moving Averages 50 (1 stock only)
//	Moving Averages 200 (1 stock only)



//Use the gnuplot functionality

require_once( '../model/include_all.php' );
require_once( '../model/stockprices.class.php' );

//Assuming this script was called by a generic screen choosing page, no options
//Order of events:
//	Show options for screen
//	Take options and generate data
//	Take data and generate graphic
//	Return graphic to user

?>

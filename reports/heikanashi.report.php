<?php

/******************************************************
*
*	Depends on:
*		classes stockprices and technicalanalysis
*		tables heikanashi and technicalanalysis
*		Data:
*
******************************************************/

if( !defined( MAX ) )
	DEFINE( 'MAX', 31 );


require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

//var_dump( $Security );
      
require_once( '../model/stockprices.class.php' );
require_once( '../model/technicalanalysis.class.php' );
$user = $Security->username;

function heikanashi_report( $days = MAX, $symbol = 'IBM' )
{

$s = new stockprices(); //Not using stockprice - uses heikanashi which is symbol, date, price ranges (open, close, high, low)
$s->querystring = " SELECT * FROM `heikanashi` WHERE symbol = '" . $symbol . "' and date > DATE_SUB(CURDATE(), INTERVAL " . $days . " DAY) order by `date` desc ";
$s->GenericQuery();

$t = new technicalanalysis();
$t->querystring = " SELECT * FROM `technicalanalysis` WHERE symbol = '" . $symbol . "' and date > DATE_SUB(CURDATE(), INTERVAL " . $days . " DAY) order by `date` desc ";
$t->GenericQuery();

$dataname = $symbol . ".heikanashi.data";
$fp = fopen( $dataname, "w" );
fwrite( $fp, "#Header line\n" );
$count = 1;
foreach( $s->resultarray as $row )
{
	$signal = "";
	foreach( $t->resultarray as $trow )
	{
		if( $trow['date'] == $row['date'] )
			$signal = $trow['candlestick'];
	}
	
	fwrite( $fp, $row['symbol'] 
			. "\t" . $row['date'] 
			. "\t" . $row['day_open'] 
			. "\t" . $row['day_close'] 
			. "\t" . $row['day_high'] 
			. "\t" . $row['day_low'] 
			. "\t\"" . $signal . "\""  
			. "\t" . $count  
			. "\n" );
	$count = 2 + abs(rand(1, $days) * rand(1, $days)) / $days;
}
fclose( $fp );

$optionsname = $symbol . ".heikanashi.gnuplot.options";
$fp = fopen( $optionsname, "w" );
//fwrite( $fp, "set terminal png medium color picsize 1200 800\n" );
fwrite( $fp, "set terminal png medium size 800,600\n" );
fwrite( $fp, "set output \"" . $symbol . ".heikanashi.png\"\n" );
fwrite( $fp, "set format x \"%m-%d\"\n" );
fwrite( $fp, "set xdata time\n" );
fwrite( $fp, "set timefmt \"%Y-%m-%d\"\n" );
fwrite( $fp, "set title \"$symbol Prices\"\n" );
fwrite( $fp, "set style fill empty\n" );
fwrite( $fp, "set ylabel \"Dollars\"\n" );
//fwrite( $fp, "set xlabel \"Date\"\n" );
fwrite( $fp, "set multiplot\n" );
//Candlestick expects 				date, open, low, high, close
fwrite( $fp, "set origin 0,0.3\n" );
fwrite( $fp, "set size 1,0.7\n" );
fwrite( $fp, "plot \"" . $dataname . "\" using 2:3:6:5:4 with candlestick title \"\"\n");
fwrite( $fp, "unset title\n" );
fwrite( $fp, "set origin 0,0\n" );
fwrite( $fp, "set size 1,0.3\n" );
fwrite( $fp, "set ylabel \"Normal Candlestick Signals - Random placement on Y axis\"\n" );
fwrite( $fp, "plot \"" . $dataname . "\" using 2:8:7 with labels title \"Daily Signals\"\n");
fwrite( $fp, "unset multiplot\n" );
fclose( $fp );

$plot = "gnuplot " . $symbol . ".heikanashi.gnuplot.options";
exec( $plot );
$cleanup = "mv $dataname $optionsname data/; mv $symbol.* $symbol/";
exec( $cleanup );
}


//test
//$symbol = 'IBM';
//heikanashis_report( MAX, $symbol );
//echo "<img src=\"$symbol.heikanashi.png\">";
?> 


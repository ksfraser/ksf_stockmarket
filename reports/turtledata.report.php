<?php

/************************************************************************************************
*
*	20100822 KF turtle data report
*	Eventum 212
*	Copied from technicalanalysis report, modified lightly 
*
*	Uses gnuplot to generate the graph
*
************************************************************************************************/


DEFINE( 'MAX', 77 );


require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

//var_dump( $Security );
      
require_once( '../model/stockprices.class.php' );
require_once( '../model/turtledata.class.php' );
$user = $Security->username;

function datafile( $days = MAX, $symbol = 'IBM' )
{

$t = new turtledata();
$t->select = "
symbol                
, date                 
, volatility
, unit
, breakouthigh20
, breakoutlow20
, breakouthigh55
, breakoutlow55
, low10
, high10
, low20
, high20
, truerange
, ignore20
, positionadd
, sellallprice
, normalizedprice";
$t->where = "symbol = '" . $symbol . "' and date > DATE_SUB(CURDATE(), INTERVAL " . $days . " DAY)";
//$t->where = "symbol = '" . $symbol . "' and date between DATE_SUB('2010-04-09', INTERVAL " . $days . " DAY) and '2010-04-09'";
$t->nolimit = TRUE;
//$t->limit = $days;
$t->orderby = "`date` desc ";
$t->Select();
//echo $t->querystring;
//echo "\n";
echo count($t->resultarray) . " rows for $symbol \n";

$filename = "turtle_" . $symbol . ".data";
$fp = fopen( $filename, "w" );
fwrite( $fp, "#Header line" );
fwrite( $fp, " \tdate \tvolatility \tunit \t\tbrkh20 \tbrkl20 \tbrkh55 \tbrkl55 \tlow10 \thigh10 \tlow20 \thigh20 \ttruerng\tignore20\tadd \tsellall\tnormalizedprice\n" );
$count = 1;
foreach( $t->resultarray as $row )
{
			$datastring = sprintf( "%.9s\t%.12s\t%.6f\t%e\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.6f\t%.2f\t%.2f\t%.2f\t%.2d\n", 
			$row['symbol'],
			$row['date'] 
			,$row['volatility']
			,$row['unit']
			,$row['breakouthigh20']
			,$row['breakoutlow20']
			,$row['breakouthigh55']
			,$row['breakoutlow55']
			,$row['low10']
			,$row['high10']
			,$row['low20']
			,$row['high20']
			,$row['truerange']
			,$row['ignore20']
			,$row['positionadd']
			,$row['sellallprice']
			,$row['normalizedprice']
			,$count
			);

			fwrite($fp, $datastring );
/*			$row['symbol']
			. "\t" . $row['date'] 
			. "\t" . $row['volatility']
			. "\t" . $row['unit']
			. "\t" . $row['breakouthigh20']
			. "\t" . $row['breakoutlow20']
			. "\t" . $row['breakouthigh55']
			. "\t" . $row['breakoutlow55']
			. "\t" . $row['low10']
			. "\t" . $row['high10']
			. "\t" . $row['low20']
			. "\t" . $row['high20']
			. "\t" . $row['truerange']
			. "\t" . $row['ignore20']
			. "\t" . $row['positionadd']
			. "\t" . $row['sellallprice']
			. "\t" . $row['normalizedprice']
			. "\t" . $count
			. "\n" );
*/
	$count++;
}
fclose( $fp );
return $filename;

}

function report_default(  $days = MAX, $symbol = 'IBM', $reporttype = "default" )
{
	$datafilename = datafile( $days, $symbol );
	
	$optionsname = $symbol . "." . $reporttype . ".gnuplot.options";
	$fp = fopen( $optionsname, "w" );
	//fwrite( $fp, "set terminal png medium color picsize 1200 800\n" );
	fwrite( $fp, "set terminal png medium size 800,900\n" );
	fwrite( $fp, "set output \"" . $symbol . ".turtledata.png\"\n" );
	fwrite( $fp, "set format x \"%m-%d\"\n" );
	fwrite( $fp, "set xdata time\n" );
	fwrite( $fp, "set timefmt \"%Y-%m-%d\"\n" );
	fwrite( $fp, "set style fill empty\n" );
	fwrite( $fp, "set ylabel \"Dollars\"\n" );
	//fwrite( $fp, "set xlabel \"Date\"\n" );
	fwrite( $fp, "set multiplot\n" );

//Breakouts
	fwrite( $fp, "set title \"$symbol Breakout prices\"\n" );
	fwrite( $fp, "set origin 0,0\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:5 with linespoints title \"Breakout High 20\" , \"" . $datafilename . "\" using 2:6 with linespoints title \"Breakout Low 20\" , \"" . $datafilename . "\" using 2:7 with linespoints title \"Breakout High 55\" , \"" . $datafilename . "\" using 2:8 with linespoints title \"Breakout Low 55\" \n");

//Prices          
	fwrite( $fp, "unset title\n" );
	fwrite( $fp, "set title \"$symbol Prices, Lows, Highs\"\n" );
	fwrite( $fp, "set origin 0,0.25\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	//fwrite( $fp, "plot \"" . $datafilename . "\" using 2:17 with linespoints title \"Normalized Price\" , \"" . $datafilename . "\" using 2:9 with linespoints title \"10 Day Low\" , \"" . $datafilename . "\" using 2:10 with linespoints title \"10 Day High\" , \"" . $datafilename . "\" using 2:11 with linespoints title \"20 Day Low\" , \"" . $datafilename . "\" using 2:12 with linespoints title \"20 Day High\"  \n");
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:9 with linespoints title \"10 Day Low\" , \"" . $datafilename . "\" using 2:10 with linespoints title \"10 Day High\" , \"" . $datafilename . "\" using 2:11 with linespoints title \"20 Day Low\" , \"" . $datafilename . "\" using 2:12 with linespoints title \"20 Day High\"  \n");

//Ranges
	fwrite( $fp, "unset title\n" );
	fwrite( $fp, "set title \"$symbol Action Price \"\n" );
	fwrite( $fp, "set origin 0,0.5\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	//fwrite( $fp, "plot \"" . $datafilename . "\" using 2:17 with linespoints title \"Normalized Price\" , \"" . $datafilename . "\" using 2:15 with linespoints title \"Position Add\" , \"" . $datafilename . "\" using 2:16 with linespoints title \"Sell All Price\"  \n");
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:15 with linespoints title \"Position Add\" , \"" . $datafilename . "\" using 2:16 with linespoints title \"Sell All Price\"  \n");

//Oscillators
	fwrite( $fp, "unset title\n" );
	fwrite( $fp, "set title \"$symbol Ranges\"\n" );
	fwrite( $fp, "set origin 0,0.75\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:13 with linespoints title \"True Range\" , \"" . $datafilename . "\" using 2:3 with linespoints title \"Volatility\"  \n");
/* **********************************************************
	fwrite( $fp, "unset multiplot\n" );
***************************************************** */
	fclose( $fp );
	
	$plot = "gnuplot " . $optionsname;
	exec( $plot );
	$cleanup = "mv $datafilename $optionsname data/; mv $symbol.* $symbol";
	exec( $cleanup );
}

/*
$symbol = 'IBM';
report( MAX, $symbol );
echo "<img src=\"$symbol.turtledata.png\">";
*/
report_default();
?> 


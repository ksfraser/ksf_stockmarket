<?php

/************************************************************************************************
*
*	20100821 KF technical analysis report
*	Eventum 211
*	Copied from candlestick report, modified heavily
*
*	Uses gnuplot to generate the graph
*
************************************************************************************************/


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

function datafile( $days = MAX, $symbol = 'IBM' )
{

$t = new technicalanalysis();
$t->select = "
symbol                
, date                 
, day_close           
, typicalprice       
, movingaverage50   
, movingaverage200 
, candlestick     
, expmovingaverage9         
, expmovingaverage12       
, expmovingaverage26      
, macd                   
, momentumoscillator    
, mamomentum           
, macrossover         
, macenterlinecrossover     
, priceoscillator          
, macd_histogram          
, linearregression       
, linearregressionangle 
, linearregressionslope
, linearregressionintercept 
, stochastic                
, relativestrenghtindex     
, rsioscillator             
, commoditychannelindex     
, pricechangepercent        
, volume12                  
, volume26                  
, volume90                  
, support12                 
, support26                 
, resistance12              
, resistance26             
, bollingerbandmiddle      
, bollingerbandupper       
, bollingerbandlower       
, bollingerpercentb        
, bollingerbandwidth       
, coefficientofvariation   
, movingaverage260         
, standarddeviation260     
, annualreturn             
, annualrisk               
, truerange                
, expmovingaverage90       
, voltrendind90            
, voltrendind26            
, volume260                
, voltrendind260   ";
$t->where = "symbol = '" . $symbol . "' and date > DATE_SUB(CURDATE(), INTERVAL " . $days . " DAY)";
//$t->where = "symbol = '" . $symbol . "' and date between DATE_SUB('2009-01-01', INTERVAL " . $days . " DAY) and '2009-04-01'";
$t->nolimit = TRUE;
//$t->limit = $days;
$t->orderby = "`date` desc ";
$t->Select();

$filename = "ta_" . $symbol . ".data";
$fp = fopen( $filename, "w" );
fwrite( $fp, "#Header line" );
fwrite( $fp, " \tdate \tday_close \ttypicalprice \tmovingaverage50 \tmovingaverage200 \tcandlestick \texpmovingaverage9 \texpmovingaverage12 \texpmovingaverage26 \tmacd \tmomentumoscillator \tmamomentum \tmacrossover \tmacenterlinecrossover \tpriceoscillator \tmacd_histogram \tlinearregression \tlinearregressionangle \tlinearregressionslope \tlinearregressionintercept \tstochastic \trelativestrenghtindex \trsioscillator \tcommoditychannelindex \tpricechangepercent \tvolume12 \tvolume26 \tvolume90 \tsupport12 \tsupport26 \tresistance12 \tresistance26 \tbollingerbandmiddle \tbollingerbandupper \tbollingerbandlower \tbollingerpercentb \tbollingerbandwidth \tcoefficientofvariation \tmovingaverage260 \tstandarddeviation260 \tannualreturn \tannualrisk \ttruerange \texpmovingaverage90 \tvoltrendind90 \tvoltrendind26 \tvolume260 \tvoltrendind260\n" );
$count = 1;
foreach( $t->resultarray as $row )
{
	fwrite( $fp, $row['symbol'] 
			. "\t" . $row['date'] 
			. "\t" . $row['day_close'] 
			. "\t" . $row['typicalprice']
			. "\t" . $row['movingaverage50']
			. "\t" . $row['movingaverage200']
			. "\t" . $row['candlestick']
			. "\t" . $row['expmovingaverage9']
			. "\t" . $row['expmovingaverage12']
			. "\t" . $row['expmovingaverage26']
			. "\t" . $row['macd']
			. "\t" . $row['momentumoscillator']
			. "\t" . $row['mamomentum']
			. "\t" . $row['macrossover']
			. "\t" . $row['macenterlinecrossover']
			. "\t" . $row['priceoscillator']
			. "\t" . $row['macd_histogram']
			. "\t" . $row['linearregression']
			. "\t" . $row['linearregressionangle']
			. "\t" . $row['linearregressionslope']
			. "\t" . $row['linearregressionintercept']
			. "\t" . $row['stochastic']
			. "\t" . $row['relativestrenghtindex']
			. "\t" . $row['rsioscillator']
			. "\t" . $row['commoditychannelindex']
			. "\t" . $row['pricechangepercent']
			. "\t" . $row['volume12']
			. "\t" . $row['volume26']
			. "\t" . $row['volume90']
			. "\t" . $row['support12']
			. "\t" . $row['support26']
			. "\t" . $row['resistance12']
			. "\t" . $row['resistance26']
			. "\t" . $row['bollingerbandmiddle']
			. "\t" . $row['bollingerbandupper']
			. "\t" . $row['bollingerbandlower']
			. "\t" . $row['bollingerpercentb']
			. "\t" . $row['bollingerbandwidth']
			. "\t" . $row['coefficientofvariation']
			. "\t" . $row['movingaverage260']
			. "\t" . $row['standarddeviation260']
			. "\t" . $row['annualreturn']
			. "\t" . $row['annualrisk']
			. "\t" . $row['truerange']
			. "\t" . $row['expmovingaverage90']
			. "\t" . $row['voltrendind90']
			. "\t" . $row['voltrendind26']
			. "\t" . $row['volume260']
			. "\t" . $row['voltrendind260']
			. "\t" . $count
			. "\n" );
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
	fwrite( $fp, "set output \"" . $symbol . ".technicalanalysis.png\"\n" );
	fwrite( $fp, "set format x \"%m-%d\"\n" );
	fwrite( $fp, "set xdata time\n" );
	fwrite( $fp, "set timefmt \"%Y-%m-%d\"\n" );
	fwrite( $fp, "set style fill empty\n" );
	fwrite( $fp, "set ylabel \"Dollars\"\n" );
	//fwrite( $fp, "set xlabel \"Date\"\n" );
	fwrite( $fp, "set multiplot\n" );
//Bollinger Bands
	fwrite( $fp, "set title \"$symbol Bollinger Bands\"\n" );
	fwrite( $fp, "set origin 0,0\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:3 with linespoints title \"Closing Price\" , \"" . $datafilename . "\" using 2:34 with linespoints title \"Middle Bollinger\" , \"" . $datafilename . "\" using 2:35 with linespoints title \"Upper Bollinger\" , \"" . $datafilename . "\" using 2:36 with linespoints title \"Lower Bollinger\" \n");

//Moving Averages	
	fwrite( $fp, "unset title\n" );
	fwrite( $fp, "set title \"$symbol Moving Averages\"\n" );
	fwrite( $fp, "set origin 0,0.25\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:5 with linespoints title \"50 Day Moving Average\" , \"" . $datafilename . "\" using 2:6 with linespoints title \"200 Day Moving Averate\" , \"" . $datafilename . "\" using 2:8 with linespoints title \"90 Day EMA\" , \"" . $datafilename . "\" using 2:9 with linespoints title \"12 Day EMA\" , \"" . $datafilename . "\" using 2:10 with linespoints title \"26 Day EMA\"  \n");

//Volumes
	fwrite( $fp, "unset title\n" );
	fwrite( $fp, "set title \"$symbol Volumes\"\n" );
	fwrite( $fp, "set origin 0,0.5\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:27 with linespoints title \"12 Day Volume Average\" , \"" . $datafilename . "\" using 2:28 with linespoints title \"26 Day Volume Average\" , \"" . $datafilename . "\" using 2:29 with linespoints title \"90 Day Volume Average\" , \"" . $datafilename . "\" using 2:40 with linespoints title \"260 Day Volume Moving Average\" , \"" . $datafilename . "\" using 2:45 with linespoints title \"90 Day Volume EMA\"  \n");

//Oscillators
	fwrite( $fp, "unset title\n" );
	fwrite( $fp, "set title \"$symbol Oscillators\"\n" );
	fwrite( $fp, "set origin 0,0.75\n" );
	fwrite( $fp, "set size 1,0.24\n" );
	fwrite( $fp, "plot \"" . $datafilename . "\" using 2:11 with linespoints title \"MACD\" , \"" . $datafilename . "\" using 2:12 with linespoints title \"Momentum Oscillator\" , \"" . $datafilename . "\" using 2:13 with linespoints title \"MA Momentum\" , \"" . $datafilename . "\" using 2:14 with linespoints title \"MA Cross-over\" , \"" . $datafilename . "\" using 2:15 with linespoints title \"MA Centreline cross-over\", \"" . $datafilename . "\" using 2:16 with linespoints title \"Price Oscillator\" , \"" . $datafilename . "\" using 2:17 with linespoints title \"MACD Histogram\",  \"" . $datafilename . "\" using 2:23 with linespoints title \"RSI\" , \"" . $datafilename . "\" using 2:24 with linespoints title \"RSI Oscillator\", \"" . $datafilename . "\" using 2:25 with linespoints title \"Commodity Channel Index\" , \"" . $datafilename . "\" using 2:39 with linespoints title \"Coefficient of Variation\"  \n");

	fwrite( $fp, "unset multiplot\n" );
	fclose( $fp );
	
	$plot = "gnuplot " . $optionsname;
	exec( $plot );
	$cleanup = "mv $datafilename $optionsname data/; mv $symbol.* $symbol";
	exec( $cleanup );
}

/*
$symbol = 'IBM';
report( MAX, $symbol );
echo "<img src=\"$symbol.technicalanalysis.png\">";
*/
//report_default();
?> 


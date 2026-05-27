<?php

//20111129 KF Bug 215 error on index -1 doesn't exist - max and min trying to reference back too many days at start of processing.  Won't fix at this time.

//calc turtle data

require_once( '../../model/include_all.php' );
require_once( '../../model/turtledata.class.php' );
require_once( '../../model/stockprices.class.php' );


function calcturtle( $symbol, $date = "2010-01-01" )
{
	echo "calcturtle Symbol $symbol starting on $date\n";
/*
	$TDAYS = 55;
	$WMULT = 7/5;
$STARTDAYS = $TDAYS * $WMULT;
*/
	$STARTDAYS = 77;
	$stockprices = new stockprices();
	//$stockprices1 = new stockprices();
	//$stockprices2 = new stockprices();
	//$stockprices3 = new stockprices();
	//$stockprices4 = new stockprices();
	$turtle = new turtledata();
//date >= DATE_SUB( '" . $prevdate . "', INTERVAL 30 DAY  )
	$stockprices->querystring = "select day_low, day_high, day_close, symbol, date from stockprices where symbol = '" . $symbol . "' and date > DATE_SUB( '" . $date . "', INTERVAL $STARTDAYS DAY ) order by date asc";
	//$stockprices->querystring = "select day_low, day_high, day_close, symbol, date from stockprices where symbol = '" . $symbol . "' and date > '" . $date . "' order by date asc";
	$stockprices->GenericQuery();
	//$count = 0;
	$prevvol = 0;
	$count = $STARTDAYS;
	while ($count < count( $stockprices->resultarray ))
	{
		if( $count == 0 )
		{
			$close1 = $stockprices->resultarray[$count]['day_close'];
			$prevdate = $stockprices->resultarray[$count]['date'];
		}
		else
		{
			$close1 = $stockprices->resultarray[$count - 1]['day_close'];
			$prevdate = $stockprices->resultarray[$count - 1]['date'];
		}
		$high = $stockprices->resultarray[$count]['day_high'];
		$low = $stockprices->resultarray[$count]['day_low'];
		$close = $stockprices->resultarray[$count]['day_close'];
	//Calc true range
		$tr1 = $high - $low;
		$tr2 = $high - $close1;
		$tr3 = $close1 - $low;
		$tr = max( $tr1, $tr2, $tr3 );
		if( $count < 1 )
		{
			$prevvol = $tr ;
		}
		$volatility = ( ( 19 * $prevvol ) + $tr ) / 20;
		$prevvol = $volatility;

		$unit = 1000 / ( $volatility * .01 ); //Prices are quoted in dollars and cents, so each "pip" is .01 dollars
		$shares = floor( $unit / $stockprices->resultarray[$count]['day_close'] ); 

		$insert['shares'] = $shares;
		$insert['unit'] = $unit;
		$insert['symbol'] = $symbol;
		$insert['date'] = $stockprices->resultarray[$count]['date'];
		$insert['volatility'] = $volatility;
		$insert['truerange'] = $tr;
//Bug 215 error on index -1
		$insert['breakouthigh20'] = max( $stockprices->resultarray[$count - 1]['day_close'],  $stockprices->resultarray[$count - 2]['day_close'], $stockprices->resultarray[$count - 3]['day_close'], $stockprices->resultarray[$count - 4]['day_close'], $stockprices->resultarray[$count - 5]['day_close'], $stockprices->resultarray[$count - 6]['day_close'], $stockprices->resultarray[$count - 7]['day_close'], $stockprices->resultarray[$count - 8]['day_close'], $stockprices->resultarray[$count - 9]['day_close'], $stockprices->resultarray[$count - 10]['day_close'], $stockprices->resultarray[$count - 11]['day_close'], $stockprices->resultarray[$count - 12]['day_close'], $stockprices->resultarray[$count - 13]['day_close'], $stockprices->resultarray[$count - 14]['day_close'], $stockprices->resultarray[$count - 15]['day_close'], $stockprices->resultarray[$count - 16]['day_close'], $stockprices->resultarray[$count - 17]['day_close'], $stockprices->resultarray[$count - 18]['day_close'], $stockprices->resultarray[$count - 19]['day_close'], $stockprices->resultarray[$count - 20]['day_close'] );
		$insert['breakoutlow20'] = min( $stockprices->resultarray[$count - 1]['day_close'],  $stockprices->resultarray[$count - 2]['day_close'], $stockprices->resultarray[$count - 3]['day_close'], $stockprices->resultarray[$count - 4]['day_close'], $stockprices->resultarray[$count - 5]['day_close'], $stockprices->resultarray[$count - 6]['day_close'], $stockprices->resultarray[$count - 7]['day_close'], $stockprices->resultarray[$count - 8]['day_close'], $stockprices->resultarray[$count - 9]['day_close'], $stockprices->resultarray[$count - 10]['day_close'], $stockprices->resultarray[$count - 11]['day_close'], $stockprices->resultarray[$count - 12]['day_close'], $stockprices->resultarray[$count - 13]['day_close'], $stockprices->resultarray[$count - 14]['day_close'], $stockprices->resultarray[$count - 15]['day_close'], $stockprices->resultarray[$count - 16]['day_close'], $stockprices->resultarray[$count - 17]['day_close'], $stockprices->resultarray[$count - 18]['day_close'], $stockprices->resultarray[$count - 19]['day_close'], $stockprices->resultarray[$count - 20]['day_close'] );
		$stoploss = $insert['breakouthigh20'] - 2 * $volatility;
		$insert['stoploss'] = $stoploss;
		$insert['high10'] = max( $stockprices->resultarray[$count - 1]['day_close'],  $stockprices->resultarray[$count - 2]['day_close'], $stockprices->resultarray[$count - 3]['day_close'], $stockprices->resultarray[$count - 4]['day_close'], $stockprices->resultarray[$count - 5]['day_close'], $stockprices->resultarray[$count - 6]['day_close'], $stockprices->resultarray[$count - 7]['day_close'], $stockprices->resultarray[$count - 8]['day_close'], $stockprices->resultarray[$count - 9]['day_close'], $stockprices->resultarray[$count - 10]['day_close'] );
		$insert['low10'] = min( $stockprices->resultarray[$count - 1]['day_close'],  $stockprices->resultarray[$count - 2]['day_close'], $stockprices->resultarray[$count - 3]['day_close'], $stockprices->resultarray[$count - 4]['day_close'], $stockprices->resultarray[$count - 5]['day_close'], $stockprices->resultarray[$count - 6]['day_close'], $stockprices->resultarray[$count - 7]['day_close'], $stockprices->resultarray[$count - 8]['day_close'], $stockprices->resultarray[$count - 9]['day_close'], $stockprices->resultarray[$count - 10]['day_close'] );
		$insert['high20'] = $insert['breakouthigh20'];
		$insert['low20'] = $insert['breakoutlow20'];
		$insert['breakouthigh55'] = max( $stockprices->resultarray[$count - 1]['day_close'],  
				$stockprices->resultarray[$count - 2]['day_close'], 
				$stockprices->resultarray[$count - 3]['day_close'], 
				$stockprices->resultarray[$count - 4]['day_close'],	
				$stockprices->resultarray[$count - 5]['day_close'],
 				$stockprices->resultarray[$count - 6]['day_close'],
 				$stockprices->resultarray[$count - 7]['day_close'],
 				$stockprices->resultarray[$count - 8]['day_close'],
 				$stockprices->resultarray[$count - 9]['day_close'],
 				$stockprices->resultarray[$count - 10]['day_close'],
 				$stockprices->resultarray[$count - 11]['day_close'],
 				$stockprices->resultarray[$count - 12]['day_close'],
 				$stockprices->resultarray[$count - 13]['day_close'],
 				$stockprices->resultarray[$count - 14]['day_close'],
 				$stockprices->resultarray[$count - 15]['day_close'],
 				$stockprices->resultarray[$count - 16]['day_close'],
 				$stockprices->resultarray[$count - 17]['day_close'],
 				$stockprices->resultarray[$count - 18]['day_close'],
 				$stockprices->resultarray[$count - 19]['day_close'],
 				$stockprices->resultarray[$count - 20]['day_close'],
 				$stockprices->resultarray[$count - 21]['day_close'],
 				$stockprices->resultarray[$count - 22]['day_close'],
 				$stockprices->resultarray[$count - 23]['day_close'],
 				$stockprices->resultarray[$count - 24]['day_close'],
 				$stockprices->resultarray[$count - 25]['day_close'],
 				$stockprices->resultarray[$count - 26]['day_close'],
 				$stockprices->resultarray[$count - 27]['day_close'],
 				$stockprices->resultarray[$count - 28]['day_close'],
 				$stockprices->resultarray[$count - 29]['day_close'],
 				$stockprices->resultarray[$count - 30]['day_close'],
 				$stockprices->resultarray[$count - 31]['day_close'],
 				$stockprices->resultarray[$count - 32]['day_close'],
 				$stockprices->resultarray[$count - 33]['day_close'],
 				$stockprices->resultarray[$count - 34]['day_close'],
 				$stockprices->resultarray[$count - 35]['day_close'],
 				$stockprices->resultarray[$count - 36]['day_close'],
 				$stockprices->resultarray[$count - 37]['day_close'],
 				$stockprices->resultarray[$count - 38]['day_close'],
 				$stockprices->resultarray[$count - 39]['day_close'],
 				$stockprices->resultarray[$count - 40]['day_close'],
 				$stockprices->resultarray[$count - 41]['day_close'],
 				$stockprices->resultarray[$count - 42]['day_close'],
 				$stockprices->resultarray[$count - 43]['day_close'],
 				$stockprices->resultarray[$count - 44]['day_close'],
 				$stockprices->resultarray[$count - 45]['day_close'],
 				$stockprices->resultarray[$count - 46]['day_close'],
 				$stockprices->resultarray[$count - 47]['day_close'],
 				$stockprices->resultarray[$count - 48]['day_close'],
 				$stockprices->resultarray[$count - 49]['day_close'],
 				$stockprices->resultarray[$count - 50]['day_close'],
 				$stockprices->resultarray[$count - 51]['day_close'],
 				$stockprices->resultarray[$count - 52]['day_close'],
 				$stockprices->resultarray[$count - 53]['day_close'],
 				$stockprices->resultarray[$count - 54]['day_close'],
 				$stockprices->resultarray[$count - 55]['day_close']
		);
		$insert['breakoutlow55'] = min( $stockprices->resultarray[$count - 1]['day_close'],  
				$stockprices->resultarray[$count - 2]['day_close'], 
				$stockprices->resultarray[$count - 3]['day_close'], 
				$stockprices->resultarray[$count - 4]['day_close'],	
				$stockprices->resultarray[$count - 5]['day_close'],
 				$stockprices->resultarray[$count - 6]['day_close'],
 				$stockprices->resultarray[$count - 7]['day_close'],
 				$stockprices->resultarray[$count - 8]['day_close'],
 				$stockprices->resultarray[$count - 9]['day_close'],
 				$stockprices->resultarray[$count - 10]['day_close'],
 				$stockprices->resultarray[$count - 11]['day_close'],
 				$stockprices->resultarray[$count - 12]['day_close'],
 				$stockprices->resultarray[$count - 13]['day_close'],
 				$stockprices->resultarray[$count - 14]['day_close'],
 				$stockprices->resultarray[$count - 15]['day_close'],
 				$stockprices->resultarray[$count - 16]['day_close'],
 				$stockprices->resultarray[$count - 17]['day_close'],
 				$stockprices->resultarray[$count - 18]['day_close'],
 				$stockprices->resultarray[$count - 19]['day_close'],
 				$stockprices->resultarray[$count - 20]['day_close'],
 				$stockprices->resultarray[$count - 21]['day_close'],
 				$stockprices->resultarray[$count - 22]['day_close'],
 				$stockprices->resultarray[$count - 23]['day_close'],
 				$stockprices->resultarray[$count - 24]['day_close'],
 				$stockprices->resultarray[$count - 25]['day_close'],
 				$stockprices->resultarray[$count - 26]['day_close'],
 				$stockprices->resultarray[$count - 27]['day_close'],
 				$stockprices->resultarray[$count - 28]['day_close'],
 				$stockprices->resultarray[$count - 29]['day_close'],
 				$stockprices->resultarray[$count - 30]['day_close'],
 				$stockprices->resultarray[$count - 31]['day_close'],
 				$stockprices->resultarray[$count - 32]['day_close'],
 				$stockprices->resultarray[$count - 33]['day_close'],
 				$stockprices->resultarray[$count - 34]['day_close'],
 				$stockprices->resultarray[$count - 35]['day_close'],
 				$stockprices->resultarray[$count - 36]['day_close'],
 				$stockprices->resultarray[$count - 37]['day_close'],
 				$stockprices->resultarray[$count - 38]['day_close'],
 				$stockprices->resultarray[$count - 39]['day_close'],
 				$stockprices->resultarray[$count - 40]['day_close'],
 				$stockprices->resultarray[$count - 41]['day_close'],
 				$stockprices->resultarray[$count - 42]['day_close'],
 				$stockprices->resultarray[$count - 43]['day_close'],
 				$stockprices->resultarray[$count - 44]['day_close'],
 				$stockprices->resultarray[$count - 45]['day_close'],
 				$stockprices->resultarray[$count - 46]['day_close'],
 				$stockprices->resultarray[$count - 47]['day_close'],
 				$stockprices->resultarray[$count - 48]['day_close'],
 				$stockprices->resultarray[$count - 49]['day_close'],
 				$stockprices->resultarray[$count - 50]['day_close'],
 				$stockprices->resultarray[$count - 51]['day_close'],
 				$stockprices->resultarray[$count - 52]['day_close'],
 				$stockprices->resultarray[$count - 53]['day_close'],
 				$stockprices->resultarray[$count - 54]['day_close'],
 				$stockprices->resultarray[$count - 55]['day_close']
		);

		$insert['sellallprice'] = min( $insert['low10'], $insert['breakoutlow20'] );
		$insert['positionadd'] = $insert['breakouthigh20'] + $volatility / 2;
	//	var_dump( $stockprices->resultarray[$count] );
	//	var_dump( $insert );
		//echo "Inserting " . $insert['stocksymbol'] . " on . " $insert['date'];
		$turtle->Insert( $insert );
		$turtle->Update( $insert );
		$count++;
		
	}
/*
*/
}
		
//TESTING
//calcturtle( "GLD" );		


?>

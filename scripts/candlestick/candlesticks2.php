<?php

//20090717 KF Calculate candlesticks

function upperthird( $row )
{
	$upperthird = $row['high'] -  ($row['high'] - $row['low']) / 3;
	if(
		$row['open'] > $upperthird
		AND
		$row['close'] > $upperthird
	)
		return 1;
	else
		return 0;
}

function lowerthird( $row )
{
	$lowerthird = $row['low'] +  ($row['high'] - $row['low']) / 3;
	if(
		$row['open'] < $lowerthird
		AND
		$row['close'] < $lowerthird
	)
		return 1;
	else
		return 0;
}


function long_candle_body( $row )
{
	//Long bodies set to 75% of trade range
	if ( 
		(100 * abs($row['close'] - $row['open']) )
		/ ($row['high'] - $row['low']) 
		> 75 
	)
		return 1;
	else
		return 0;
}
function short_candle_body( $row )
{
	//Short bodies set to 50% of trade range
	if ( 
		(100 * abs($row['close'] - $row['open']) )
		/ ($row['high'] - $row['low']) 
		< 50 
	)
		return 1;
	else
		return 0;
}

function today_white( $row )
{
	//Return either 1 or 0 if yesterday's candle was white
	if ($row['close'] > $row['open'] )
		return 1;
	else
		return 0;
}
function today_black( $row )
{
	//Return either 1 or 0 if yesterday's candle was black
	if ($row['close'] < $row['open'] )
		return 1;
	else
		return 0;
}
function yesterday_white( $row )
{
	//Return either 1 or 0 if yesterday's candle was white
	if ($row['close1'] > $row['open1'] )
		return 1;
	else
		return 0;
}
function yesterday_black( $row )
{
	//Return either 1 or 0 if yesterday's candle was black
	if ($row['close1'] < $row['open1'] )
		return 1;
	else
		return 0;
}

function uptrend( $row )
{
	if( 
		//$row['close'] > $row['open'] 
		//AND $row['close'] > $row['close1'] 
		$row['close1'] > $row['close2'] 
		AND $row['close2'] > $row['close3'] 
	)
		return 1;
	else
		return 0;
}
function downtrend( $row )
{
	if( 
		//$row['close'] < $row['open'] 
		//AND $row['close'] < $row['close1'] 
		$row['close1'] < $row['close2'] 
		AND $row['close2'] < $row['close3'] 
	)
		return 1;
	else
		return 0;
}

function engulfing( $row )
{
//Checking if today engulfs yesterday.  Don't care colors since that will be
//taken care of using today_white ...
	if ($row['open'] > $row['close'])
	{
		$todaymax = $row['open'];
		$todaymin = $row['close'];
	}
	else
	{
		$todaymin = $row['open'];
		$todaymax = $row['close'];
	}
	if ($row['open1'] > $row['close1'])
	{
		$yesterdaymax = $row['open1'];
		$yesterdaymin = $row['close1'];
	}
	else
	{
		$yesterdaymin = $row['open1'];
		$yesterdaymax = $row['close1'];
	}
	if( 
		$todaymax > $yesterdaymax
		and $todaymin < $yesterdaymin
	)
		return 1;
	else
		return 0;
}
function harami( $row )
{
//Checking if yesterday engulfs today.  Don't care colors since that will be
//taken care of using today_white ...
	if ($row['open'] > $row['close'])
	{
		$todaymax = $row['open'];
		$todaymin = $row['close'];
	}
	else
	{
		$todaymin = $row['open'];
		$todaymax = $row['close'];
	}
	if ($row['open1'] > $row['close1'])
	{
		$yesterdaymax = $row['open1'];
		$yesterdaymin = $row['close1'];
	}
	else
	{
		$yesterdaymin = $row['open1'];
		$yesterdaymax = $row['close1'];
	}
	if( 
		$todaymax < $yesterdaymax
		and $todaymin > $yesterdaymin
	)
		return 1;
	else
		return 0;
}

function Heikin_Ashi ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
	//Heikin Ashi candlesticks are modified.
	//    	xClose = (Open+High+Low+Close)/4
      	//	o Average price of the current bar

    	//	xOpen = [xOpen(Previous Bar) + Close(Previous Bar)]/2
      	//	o Midpoint of the previous bar

    	//	xHigh = Max(High, xOpen, xClose)
      	//	o Highest value in the set

    	//	xLow = Min(Low, xOpen, xClose)
      	//	Lowest value in the set

	// *  Hollow candles with no lower "shadows" indicate a strong uptrend: let your profits ride!
    	// * Hollow candles signify an uptrend: you might want to add to your long position, and exit short positions.
    	// * One candle with a small body surrounded by upper and lower shadows indicates a trend change: risk-loving traders might buy or sell here, while others will wait for confirmation before going short or long.
    	// * Filled candles indicate a downtrend: you might want to add to your short position, and exit long positions.
    	// * Filled candles with no higher shadows identify a strong downtrend: stay short until there's a change in trend.

	

//	if ($row['open'] == $row['close'] ) 
//			return "Heikin_Ashi";
//		else
//			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Heikin_Ashi";
$fcnallert['Heikin_Ashi']= "Heikin_Ashi pattern found.";
$fcnaction['Heikin_Ashi'] = "Alert";

function Perfect_Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if ($row['open'] == $row['close'] ) 
			return "Doji";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Perfect_Doji";
$fcnallert['Perfect_Doji']= "Perfect Doji pattern found.  The Perfect Doji pattern indicates uncertainty.  This is a heads up to be looking for a trend reversal.";
$fcnaction['Perfect_Doji'] = "Alert";

function Double_Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if(
			Yesterday_Doji( $row ) and Doji( $row )
		)
			return "Double_Doji";
		else
			return NULL;
	}
	return NULL;
}
$fcnlist[]= "Double_Doji";
$fcnallert['Double_Doji']= "Double_Doji pattern found.  The Double_Doji pattern indicates uncertainty followed by a significant move. Buy Straddles.";
$fcnaction['Double_Doji'] = "Alert";

function Yesterday_Doji ( $row = NULL )
{
	//($row['open1']= $row['close1'] ) 
	if( $row != NULL )
        {
		if ( 
			(ABS($row['open1'] - $row['close1'] ) <= (($row['high1'] -$row['low1']) * 0.1))
		)
			return "Yesterday_Doji";
		else
			return NULL;
	}
	return NULL;
}
$fcnlist[]= "Yesterday_Doji";
$fcnallert['Yesterday_Doji']= "Yesterday_Doji pattern found.  The Yesterday_Doji pattern indicates uncertainty.  This is a heads up to be looking for a trend reversal.";
$fcnaction['Yesterday_Doji'] = "Alert";

function Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if (
			( yesterday_white($row) ) 
			AND (ABS($row['open'] - $row['close'] ) <= (($row['high'] -$row['low']) * 0.1))
		)
			return "Doji";
		else
			return NULL;
	}
	return NULL;
}
$fcnlist[]= "Doji";
$fcnallert['Doji']= "Doji pattern found.  The Doji pattern indicates uncertainty.  This is a heads up to be looking for a trend reversal.";
$fcnaction['Doji'] = "Alert";

function White_Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if (
		 	( yesterday_white($row) ) 
			AND (ABS($row['open'] - $row['close'] ) <= (($row['high'] -$row['low']) * 0.1))
		)
			return "White_Doji";
		else
			return NULL;
	}
	return NULL;
}
$fcnlist[]= "White_Doji";
$fcnallert['White_Doji']= "White_Doji pattern found.  The White_Doji pattern indicates the top of an uptrend.  This is a heads up to be looking for a trend reversal. Buy puts, buy call calendar spreads, short the stock or sell calls.";
$fcnaction['White_Doji'] = "sellstock";

function Black_Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if (
			( yesterday_black($row) ) 
			AND 
			(ABS($row['open'] - $row['close'] ) <= (($row['high'] -$row['low']) * 0.1))
		)
			return "Black_Doji";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Black_Doji";
$fcnallert['Black_Doji']= "Black_Doji pattern found.  The Black_Doji pattern indicates the bottom of a downtrend.  This is a heads up to be looking for a trend reversal. Buy calls, buy put calendar spreads, buy the stock or sell expensive puts.";

$fcnaction['Black_Doji'] = "buystock";

function Doji_Near ( $row = NULL )
{
//(ABS($row['open'] - $row['close'] ) <= (($row['high'] -$row['low']) * 0.1)) 
	if( $row != NULL )
        {
		if(ABS($row['open'] - $row['close'] ) <= (($row['high'] -$row['low']) * 0.1)) 
			return "Doji_Near";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Doji_Near";
$fcnallert['Doji_Near']= "Doji_Near pattern found.  The Doji_Near pattern indicates ...";
$fcnaction['Doji_Near'] = "Alert";

function Bullish_Engulfing ( $row = NULL )
{
//(($row['open1'] > $row['close1']) AND ($row['close'] > $row['open']) AND ($row['close'] >= $row['open1']) AND ($row['close1'] >= $row['open']) AND (($row['close'] - $row['open']) > ($row['open1'] - $row['close1']))) 
	if( $row != NULL )
        {
		if(
			($row['open1'] > $row['close1']) 
			AND ($row['close'] > $row['open']) 
			AND ($row['close'] >= $row['open1']) 
			AND ($row['close1'] >= $row['open']) 
			AND (
				($row['close'] - $row['open']) > ($row['open1'] - $row['close1'])
			)
		) 
			return "Bullish_Engulfing";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Bullish_Engulfing";
$fcnallert['Bullish_Engulfing']= "Bullish_Engulfing pattern found.  The Bullish_Engulfing pattern indicates the end of a downtrend.  This is a heads up to check that this stock was in a downtrend. Buy calls, buy put calendar spreads, buy the stock or sell expensive puts.";
$fcnaction['Bullish_Engulfing'] = "buystock";

function Bearish_Engulfing ( $row = NULL )
{
//(($row['open1'] > $row['close1']) AND ($row['close'] > $row['open']) AND ($row['close'] >= $row['open1']) AND ($row['close1'] >= $row['open']) AND (($row['close'] - $row['open']) > ($row['open1'] - $row['close1']))) 
	if( $row != NULL )
        {
		if(
			yesterday_white( $row ) AND today_black( $row ) AND engulfing( $row )
		) 
			return "Bearish_Engulfing";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Bearish_Engulfing";
$fcnallert['Bearish_Engulfing']= "Bearish_Engulfing pattern found.  The Bearish_Engulfing pattern indicates the end of an uptrend.  This is a heads up to check that this stock was in an uptrend that is ending.  Buy puts, buy call calendar spreads, short the stock or sell calls.";
$fcnaction['Bearish_Engulfing'] = "sellstock";


function Hammer ( $row = NULL )
{
	if( $row != NULL )
        {
		if(
			upperthird( $row )
			AND
			downtrend( $row )
		) 
			return "Hammer";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Hammer";
$fcnallert['Hammer']= "Hammer pattern found.  The Hammer pattern indicates the price is trying to gauge the depth. This would suggest the bottom of a decline.  Black bodies (close lower than open) indicates Bearish indicators, and a white body indicates Bullish.  The Hammer is usually at the bottom of a downtrend. Buy calls or ATM Put Calendar Spreads or buy the stock or sell expensive puts for up trends. Buy puts or sell expensive calls for down trends ";
$fcnaction['Hammer'] = "buystock";


function Hanging_Man ( $row = NULL )
{
	if( $row != NULL )
        {
		if(
			upperthird( $row )
			AND
			uptrend( $row )
		) 
			return "Hanging_Man";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Hanging_Man";
$fcnallert['Hanging_Man']= "Hanging_Man pattern found.  The Hanging_Man pattern indicates the price is trying to gauge the top. This would suggest the top of a run-up.  Black bodies (close lower than open) indicates Bearish indicators, and a white body indicates Bullish.  The Hanging Man is usually at the top of an uptrend.";
$fcnaction['Hanging_Man'] = "sellstock";


function Piercing_Line ( $row = NULL )
{
//(($row['close1'] < $row['open1']) AND ((($row['open1'] + $row['close1']) / 2) < $row['close']) AND ($row['open'] < $row['close']) AND ($row['open'] < $row['close1']) AND ($row['close'] < $row['open1']) AND (($row['close'] - $row['open']) / (.001 + ($row['high'] - $row['low'])) > 0.6)) 
	if( $row != NULL )
        {
		if(($row['close1'] < $row['open1']) AND ((($row['open1'] + $row['close1']) / 2) < $row['close']) AND ($row['open'] < $row['close']) AND ($row['open'] < $row['close1']) AND ($row['close'] < $row['open1']) AND (($row['close'] - $row['open']) / (.001 + ($row['high'] - $row['low'])) > 0.6)) 
			return "Piercing_Line";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Piercing_Line";
$fcnallert['Piercing_Line']= "Piercing_Line pattern found.  The Piercing_Line pattern is a bottom reversal. It is a two candle pattern at the end of a declining market. The first day real body is black. The second day is a long white body. The white day opens sharply lower, under the trading range of the previous day. The price comes up to where it closes above the 50% level of the black body. ";
$fcnaction['Piercing_Line'] = "buystock";


function Dark_Cloud ( $row = NULL )
{
//(($row['close1'] > $row['open1']) AND ((($row['close1'] + $row['open1']) / 2) > $row['close']) AND ($row['open'] > $row['close']) AND ($row['open'] > $row['close1']) AND ($row['close'] > $row['open1']) AND (($row['open'] - $row['close']) / (.001 + ($row['high'] - $row['low'])) > .6)) 
	if( $row != NULL )
        {
		if(($row['close1'] > $row['open1']) AND ((($row['close1'] + $row['open1']) / 2) > $row['close']) AND ($row['open'] > $row['close']) AND ($row['open'] > $row['close1']) AND ($row['close'] > $row['open1']) AND (($row['open'] - $row['close']) / (.001 + ($row['high'] - $row['low'])) > .6)) 
			return "Dark_Cloud";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Dark_Cloud";
$fcnallert['Dark_Cloud']= "Dark_Cloud pattern found.  The Dark Cloud Cover is a two-day bearish pattern found at the end of an upturn or at the top of a congested trading area. The first day of the pattern is a strong white real body. The second day's price opens higher than any of the previous day's trading range, but is a black body.";
$fcnaction['Dark_Cloud'] = "sellstock";


function Bullish_Harami ( $row = NULL )
{
//(($row['open1'] > $row['close1']) AND ($row['close'] > $row['open']) AND ($row['close'] <= $row['open1']) AND ($row['close1'] <= $row['open']) AND (($row['close'] - $row['open']) < ($row['open1'] - $row['close1']))) 
	if( $row != NULL )
        {
		if (
			yesterday_black( $row ) AND today_white( $row ) AND harami( $row )
		)
			return "Bullish_Harami";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Bullish_Harami";
$fcnallert['Bullish_Harami']= "Bullish_Harami pattern found. Means 'Pregnant Woman'. It is the opposite of an Engulfing Pattern. In this pattern the Black candlestick engulfs the next day's White candlestick, or vice versus for the colors. Indicates a change in sentiment. The location of the 2nd candlestick within the 1st gives some indication of the strength of the new sentiment. The Bullish_Harami pattern indicates  Buy calls, buy put calendar spreads, buy the stock or sell expensive puts.";
$fcnaction['Bullish_Harami'] = "buystock";


function Bearish_Harami ( $row = NULL )
{
//(($row['close1'] > $row['open1']) AND ($row['open'] > $row['close']) AND ($row['open'] <= $row['close1']) AND ($row['open1'] <= $row['close']) AND (($row['open'] - $row['close']) < ($row['close1'] - $row['open1']))) 
	if( $row != NULL )
        {
		if(
			yesterday_white( $row ) AND today_black( $row ) AND harami( $row )
		)
			return "Bearish_Harami";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Bearish_Harami";
$fcnallert['Bearish_Harami']= "Bearish_Harami pattern found. Means 'Pregnant Woman'. It is the opposite of an Engulfing Pattern. In this pattern the Black candlestick engulfs the next day's White candlestick, or vice versus for the colors. Indicates a change in sentiment. The location of the 2nd candlestick within the 1st gives some indication of the strength of the new sentiment.  The Bearish_Harami pattern indicates  Buy puts, buy call calendar spreads, short the stock or sell calls.";
$fcnaction['Bearish_Harami'] = "sellstock";

function Morning_Star ( $row = NULL )
{
//(($row['open2']>$row['close2'])AND(($row['open2']-$row['close2'])/(.001+$row['high2']-$row['low2'])>.6)AND($row['close2']>$row['open1'])AND($row['open1']>$row['close1'])AND(($row['high1']-$row['low1'])>(3*($row['close1']-$row['open1'])))AND(C>$row['open'])AND($row['open']>$row['open1'])) 
	if( $row != NULL )
        {
		if(($row['open2']>$row['close2'])AND(($row['open2']-$row['close2'])/(.001+$row['high2']-$row['low2'])>.6)AND($row['close2']>$row['open1'])AND($row['open1']>$row['close1'])AND(($row['high1']-$row['low1'])>(3*($row['close1']-$row['open1'])))AND($row['close']>$row['open'])AND($row['open']>$row['open1'])) 
			return "Morning_Star";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Morning_Star";
$fcnallert['Morning_Star']= "Morning_Star pattern found. Black candlestick, followed by a white lower than the black, followed by a white higher than the 1st white.  The Morning Star is a bottom reversal signal. Like the morning star, the planet Mercury, it foretells the sunrise, or the rising prices. The pattern consists of a three day signal.  The Morning_Star pattern indicates ...";
$fcnaction['Morning_Star'] = "buystock";


function Evening_Star ( $row = NULL )
{
//(($row['close2'] > $row['open2']) AND (($row['close2'] - $row['open2']) / (.001 + $row['high2'] - $row['low2']) > .6) AND ($row['close2'] < $row['open1']) AND ($row['close1'] > $row['open1']) AND (($row['high1'] - $row['low1']) > (3 * ($row['close1'] - $row['open1']))) AND ($row['open'] > $row['close']) AND ($row['open'] < $row['open1'])) 
	if( $row != NULL )
        {
		if(($row['close2'] > $row['open2']) AND (($row['close2'] - $row['open2']) / (.001 + $row['high2'] - $row['low2']) > .6) AND ($row['close2'] < $row['open1']) AND ($row['close1'] > $row['open1']) AND (($row['high1'] - $row['low1']) > (3 * ($row['close1'] - $row['open1']))) AND ($row['open'] > $row['close']) AND ($row['open'] < $row['open1'])) 
			return "Evening_Star";
		else
			return NULL;
	
	}
	return NULL;
}

$fcnlist[]= "Evening_Star";
$fcnallert['Evening_Star']= "Evening_Star pattern found. A white candlestick, a higher white, followed by a black.  The Evening Star is the exact opposite of the morning star. The evening star, the planet Venus, occurs just before the darkness sets in. The evening star is found at the end of the uptrend.  The Evening_Star pattern indicates ...";
$fcnaction['Evening_Star'] = "sellstock";

function Bullish_Kicker ( $row = NULL )
{
//($row['open1'] > $row['close1']) AND ($row['open'] >= $row['open1']) AND ($row['close'] > $row['open']) 
	if( $row != NULL )
        {
		if(
			($row['open1'] > $row['close1']) 
			AND ($row['open'] >= $row['open1']) 
			AND ($row['close'] > $row['open']) 
		)
			return "Bullish_Kicker";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Bullish_Kicker";
$fcnallert['Bullish_Kicker']= "Bullish_Kicker pattern found. The first day's open and the second day's open are the same BUT the price movement is in opposite directions.  Pattern Psychology: The Kicker Signal demonstrates a dramatic change in investor sentiment. The longer the candles, the more dramatic the price reversal.  The Bullish_Kicker pattern indicates ...";
$fcnaction['Bullish_Kicker'] = "buystock";

function Bearish_Kicker ( $row = NULL )
{
//($row['open1'] < $row['close1']) AND ($row['open'] <= $row['open1']) AND ($row['close'] <= $row['open']) 
	if( $row != NULL )
        {
		if(
			($row['open1'] < $row['close1']) 
			AND ($row['open'] <= $row['open1']) 
			AND ($row['close'] <= $row['open']) 
		)
			return "Bearish_Kicker";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Bearish_Kicker";
$fcnallert['Bearish_Kicker']= "Bearish_Kicker pattern found. The first day's open and the second day's open are the same BUT the price movement is in opposite directions.  Pattern Psychology: The Kicker Signal demonstrates a dramatic change in investor sentiment. The longer the candles, the more dramatic the price reversal.  The Bearish_Kicker pattern indicates ...";
$fcnaction['Bearish_Kicker'] = "sellstock";

function Shooting_Star ( $row = NULL )
{
//((($row['high'] - $row['low']) > 4 * ($row['open'] - $row['close'])) AND (($row['high'] - $row['close']) / (.001 +$row['high']- $row['low']) >= 0.75) AND (($row['high'] - $row['open']) / (.001 +$row['high']- $row['low']) >= 0.75))) 
	if( $row != NULL )
        {
		if(
			(
				($row['high'] - $row['low']) 
				> 4 * ($row['open'] - $row['close'])
			) 
			AND (
				(
					($row['high'] - $row['close']) 
					/ (.001 +$row['high']- $row['low']) 
				)>= 0.75
			) 
			AND (
				(
					($row['high'] - $row['open']) 
					/ (.001 +$row['high']- $row['low']) 
				) >= 0.75
			)
			AND (
				//uptrend
				( ($row['high']+$row['low']) / 2 > ($row['high1']+$row['low1']) )
				AND ( ($row['high1']+$row['low1']) / 2 > ($row['high2']+$row['low2']) )
			)
		) 
			return "Shooting_Star";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Shooting_Star";
$fcnallert['Shooting_Star']= "Shooting_Star pattern found.  One candle pattern appearing in an uptrend. The shadow (or tail) should be at least two times the length of the body. The color of the body is not important, although a black body has slightly more Bearish indications.  Pattern Psychology: After a strong uptrend the Bulls appear to still be in control with price opening higher, but by the end of the day the Bears step in and take the price back down to the lower end of the trading range. Lower trading the next day reinforces the probability of a pullback.  A shooting star is a series of higher and higher climbing white candlesticks.  A Shooting Star sends a warning that the top is near. It got its name by looking like a shooting star.  The Shooting_Star pattern indicates ...";
$fcnaction['Shooting_Star'] = "sellstock";

function Inverted_Hammer ( $row = NULL )
{
	if( $row != NULL )
        {
		if(
			lowerthird( $row )
			AND
			downtrend( $row )
		) 
			return "Inverted_Hammer";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Inverted_Hammer";
$fcnallert['Inverted_Hammer'] = "Inverted_Hammer pattern found.   One candle pattern appearing in an uptrend. The shadow (or tail) should be at least two times the length of the body. The color of the body is not important, although a black body has slightly more Bearish indications.  Pattern Psychology: After a strong uptrend the Bulls appear to still be in control with price opening higher, but by the end of the day the Bears step in and take the price back down to the lower end of the trading range. Lower trading the next day reinforces the probability of a pullback.  A shooting star is a series of higher and higher climbing white candlesticks.  A Shooting Star sends a warning that the top is near. It got its name by looking like a shooting star. The Shooting Star Formation, at the bottom of a trend, is a bullish signal. It is known as an inverted hammer. It is important to wait for the bullish verification. The Inverted_Hammer pattern indicates Buy calls or ATM Put Calendar Spreads or buy the stock or sell expensive puts for up trends ";
$fcnaction['Inverted_Hammer'] = "buystock";

function candlestick( $row = "test" )
{
	global $fcnlist;
	global $fcnallert;
	$result = array();
	$count = 0;
	if( $row != NULL )
	{
		//check each row for each candlestick
//		var_dump( $fcnlist );
		foreach( $fcnlist as $fcncount => $func )
		{
			$res = $func( $row );
			if( $res != NULL )
			{
				$result[$row['symbol']][$row['date']][$func]= $fcnallert[ $res ];
			}
			else
			{
				//for testing purposes to see that the functions were entered, uncomment
				//$result[$row['symbol']][$row['date']][$func]= "";
			}
		}
	}
//	var_dump( $result );
	return $result;
}

//$text = candlestick( "TEST" );
//var_dump( $text );

/****************************************************************************
*
*	To put the details and actions into a table
*
	echo __FILE__ . "\n";
	require_once( '../local.php' );
	Local_Init();
	require_once( 'data/generictable.php' );
	require_once('security/genericsecurity.php');
	global $Security;
	require_once( '../../model/candlestickactions.class.php' );
	$c = new candlestickactions();
	foreach( $fcnlist as $value )
	{
		$insert['candlestick_name'] = $value;
		$insert['candlestick_name11'] = $value;
		$insert['candlestick_detail'] = $fcnallert[$value];
		$insert['candlestick_action'] = $fcnaction[$value];
		var_dump( $insert );
		$c->Insert( $insert );
	}
*
******************************************************************************/


/*
Candle - 3 Black Crows
If(Ref((OPEN-C),-2)>Mov(Abs(OPEN-C),10,S), {long black}
If(Ref((OPEN-C),-1)>Mov(Abs(OPEN-C),10,S), {long black}
If((OPEN-C)>Mov(Abs(OPEN-C),10,S), {long black}
If(Ref((Abs(OPEN+C)/2),-1)<Ref((Abs(OPEN+C)/2),-2), {lower midpoint}
If((Abs(OPEN+C)/2)<Ref((Abs(OPEN+C)/2),-1), {lower midpoint}
-1,0),0),0),0),0)

Candle - 3 White Soldiers
If(Ref((C-OPEN),-2)>Mov(Abs(OPEN-C),10,S), {long white}
If(Ref((C-OPEN),-1)>Mov(Abs(OPEN-C),10,S), {long white}
If((C-OPEN)>Mov(Abs(OPEN-C),10,S), {long white}
If(Ref((Abs(OPEN+C)/2),-1)>Ref((Abs(OPEN+C)/2),-2), {higher midpoint}
If((Abs(OPEN+C)/2)>Ref((Abs(OPEN+C)/2),-1), {higher midpoint}
1,0),0),0),0),0)

Candle - 3 Crows & Soldiers
If((Fml("Candle - 3 Black Crows")),-1,If((Fml("Candle - 3 White Soldiers")),1,0))
function Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if ($row['open'] == $row['close'] ) 
			return "Doji";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Doji";
$fcnallert['Doji']= "Doji pattern found.  The Doji pattern indicates uncertainty.  This is a heads up to be looking for a trend reversal.";
$fcnaction['Doji'] = "Alert";

function Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if ($row['open'] == $row['close'] ) 
			return "Doji";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Doji";
$fcnallert['Doji']= "Doji pattern found.  The Doji pattern indicates uncertainty.  This is a heads up to be looking for a trend reversal.";
$fcnaction['Doji'] = "Alert";

function Doji ( $row = NULL )
{
	//($row['open']= $row['close'] ) 
	if( $row != NULL )
        {
		if ($row['open'] == $row['close'] ) 
			return "Doji";
		else
			return NULL;
	}
	return NULL;
}

$fcnlist[]= "Doji";
$fcnallert['Doji']= "Doji pattern found.  The Doji pattern indicates uncertainty.  This is a heads up to be looking for a trend reversal.";
$fcnaction['Doji'] = "Alert";


**********************
As Support/Resistance lines are being reached or a trend reversal is approaching, the shadow lines get longer.
ShadowResistance:=If(OPEN<CLOSE,(HIGH-CLOSE),(HIGH-OPEN));
Mov(ShadowResistance,3,S); {for not so short-term results, use:
Mov(ShadowResistance,10,w)}

ShadowSupport:=If(CLOSE>OPEN,(OPEN-LOW),(CLOSE-LOW)); 
Mov(ShadowSupport,3,S); 
{for not so short-term results, use: Mov(ShadowSupport,10,w)}
*/

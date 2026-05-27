<?php

//20090717 KF Calculate candlesticks

/*




*/

//$fcnlist = array();
//$fcnallert = array();

function Doji ( $row = NULL )
{
	//(O = C ) 
	if( $row != NULL )
        {
		return "Doji";
	}
	return NULL;
}

$fcnlist[] = "Doji";
$fcnallert['Doji'] = "Doji pattern found.  The Doji pattern indicates ...";

function Doji_Yesterday ( $row = NULL )
{
//(O1 = C1 ) 
	if( $row != NULL )
        {
		return "Doji_Yesterday";
	}
	return NULL;
}

$fcnlist[] = "Doji_Yesterday";
$fcnallert['Doji_Yesterday'] = "Doji_Yesterday pattern found.  The Doji_Yesterday pattern indicates ...";

function Doji_Near ( $row = NULL )
{
//(ABS(O - C ) <= ((H - L ) * 0.1)) 
	if( $row != NULL )
        {
		return "Doji_Near";
	}
	return NULL;
}

$fcnlist[] = "Doji_Near";
$fcnallert['Doji_Near'] = "Doji_Near pattern found.  The Doji_Near pattern indicates ...";

function Bullish_Engulfing ( $row = NULL )
{
//((O1 > C1) AND (C > O) AND (C >= O1) AND (C1 >= O) AND ((C - O) > (O1 - C1))) 
	if( $row != NULL )
        {
		return "Bullish_Engulfing";
	}
	return NULL;
}

$fcnlist[] = "Bullish_Engulfing";
$fcnallert['Bullish_Engulfing'] = "Bullish_Engulfing pattern found.  The Bullish_Engulfing pattern indicates ...";


function Hammer ( $row = NULL )
{
//(((H-L)>3*(O-C)AND((C-L)/(.001+H-L)>0.6)AND((O-L)/(.001+H-L)>0.6))) 
	if( $row != NULL )
        {
		return "Hammer";
	}
	return NULL;
}

$fcnlist[] = "Hammer";
$fcnallert['Hammer'] = "Hammer pattern found.  The Hammer pattern indicates ...";


function Hanging_Man ( $row = NULL )
{
//(((H - L) > 4 * (O - C)) AND ((C - L) / (.001 + H - L) >= 0.75) AND ((O - L) / (.001 + H - L) >= .075))) 
	if( $row != NULL )
        {
		return "Hanging_Man";
	}
	return NULL;
}

$fcnlist[] = "Hanging_Man";
$fcnallert['Hanging_Man'] = "Hanging_Man pattern found.  The Hanging_Man pattern indicates ...";


function Piercing_Line ( $row = NULL )
{
//((C1 < O1) AND (((O1 + C1) / 2) < C) AND (O < C) AND (O < C1) AND (C < O1) AND ((C - O) / (.001 + (H - L)) > 0.6)) 
	if( $row != NULL )
        {
		return "Piercing_Line";
	}
	return NULL;
}

$fcnlist[] = "Piercing_Line";
$fcnallert['Piercing_Line'] = "Piercing_Line pattern found.  The Piercing_Line pattern indicates ...";


function Dark_Cloud ( $row = NULL )
{
//((C1 > O1) AND (((C1 + O1) / 2) > C) AND (O > C) AND (O > C1) AND (C > O1) AND ((O - C) / (.001 + (H - L)) > .6)) 
	if( $row != NULL )
        {
		return "Dark_Cloud";
	}
	return NULL;
}

$fcnlist[] = "Dark_Cloud";
$fcnallert['Dark_Cloud'] = "Dark_Cloud pattern found.  The Dark_Cloud pattern indicates ...";


function Bullish_Harami ( $row = NULL )
{
//((O1 > C1) AND (C > O) AND (C <= O1) AND (C1 <= O) AND ((C - O) < (O1 - C1))) 
	if( $row != NULL )
        {
		return "Bullish_Harami";
	}
	return NULL;
}

$fcnlist[] = "Bullish_Harami";
$fcnallert['Bullish_Harami'] = "Bullish_Harami pattern found.  The Bullish_Harami pattern indicates ...";


function Bearish_Harami ( $row = NULL )
{
//((C1 > O1) AND (O > C) AND (O <= C1) AND (O1 <= C) AND ((O - C) < (C1 - O1))) 
	if( $row != NULL )
        {
		return "Bearish_Harami";
	}
	return NULL;
}

$fcnlist[] = "Bearish_Harami";
$fcnallert['Bearish_Harami'] = "Bearish_Harami pattern found.  The Bearish_Harami pattern indicates ...";

function Morning_Star ( $row = NULL )
{
//((O2>C2)AND((O2-C2)/(.001+H2-L2)>.6)AND(C2>O1)AND(O1>C1)AND((H1-L1)>(3*(C1-O1)))AND(C>O)AND(O>O1)) 
	if( $row != NULL )
        {
		return "Morning_Star";
	}
	return NULL;
}

$fcnlist[] = "Morning_Star";
$fcnallert['Morning_Star'] = "Morning_Star pattern found.  The Morning_Star pattern indicates ...";


function Evening_Star ( $row = NULL )
{
//((C2 > O2) AND ((C2 - O2) / (.001 + H2 - L2) > .6) AND (C2 < O1) AND (C1 > O1) AND ((H1 - L1) > (3 * (C1 - O1))) AND (O > C) AND (O < O1)) 
	if( $row != NULL )
        {
		return "Evening_Star";
	}
	return NULL;
}

$fcnlist[] = "Evening_Star";
$fcnallert['Evening_Star'] = "Evening_Star pattern found.  The Evening_Star pattern indicates ...";

function Bullish_Kicker ( $row = NULL )
{
//(O1 > C1) AND (O >= O1) AND (C > O) 
	if( $row != NULL )
        {
		return "Bullish_Kicker";
	}
	return NULL;
}

$fcnlist[] = "Bullish_Kicker";
$fcnallert['Bullish_Kicker'] = "Bullish_Kicker pattern found.  The Bullish_Kicker pattern indicates ...";

function Bearish_Kicker ( $row = NULL )
{
//(O1 < C1) AND (O <= O1) AND (C <= O) 
	if( $row != NULL )
        {
		return "Bearish_Kicker";
	}
	return NULL;
}

$fcnlist[] = "Bearish_Kicker";
$fcnallert['Bearish_Kicker'] = "Bearish_Kicker pattern found.  The Bearish_Kicker pattern indicates ...";

function Shooting_Star ( $row = NULL )
{
//(((H - L) > 4 * (O - C)) AND ((H - C) / (.001 + H - L) >= 0.75) AND ((H - O) / (.001 + H - L) >= 0.75))) 
	if( $row != NULL )
        {
		return "Shooting_Star";
	}
	return NULL;
}

$fcnlist[] = "Shooting_Star";
$fcnallert['Shooting_Star'] = "Shooting_Star pattern found.  The Shooting_Star pattern indicates ...";

function Inverted_Hammer ( $row = NULL )
{
//(((H - L) > 3 * (O - C)) AND ((H - C) / (.001 + H - L) > 0.6) AND ((H - O) / (.001 + H - L) > 0.6))) 
	if( $row != NULL )
        {
		return "Inverted_Hammer";
	}
	return NULL;
}

$fcnlist[] = "Inverted_Hammer";
$fcnallert['Inverted_Hammer'] = "Inverted_Hammer pattern found.  The Inverted_Hammer pattern indicates ...";

function candlestick( $row = "test" )
{
	global $fcnlist;
	$result = array();
	$count = 0;
	if( $row != NULL )
	{
		//check each row for each candlestick
	//	var_dump( $fcnlist );
		foreach( $fcnlist as $fcncount => $func )
		{
			$result[] = $func( $row );
			$count++;
//			var_dump( $result );
		}
	}
//	foreach( $result as $c => $key )
//	{
//		$resulttext[] = $fcnallert[$key];
//	}
//	return $resulttext;
	return $result;
}

$text = candlestick( "TEST" );
var_dump( $text );

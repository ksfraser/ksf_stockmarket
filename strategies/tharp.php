<?php
/*
Example:

Tom Basso designed a simple, random-entry trading system … We determined the volatility of the market by a 10-day exponential moving average of the average true range. Our initial stop was three times that volatility reading.

Once entry occurred by a coin flip, the same three-times-volatility stop was trailed from the close. However, the stop could only move in our favor. Thus, the stop moved closer whenever the markets moved in our favor or whenever volatility shrank. We also used a 1% risk model for our position-sizing system…

We ran it on 10 markets. And it was always, in each market, either long or short depending upon a coin flip… It made money 100% of the time when a simple 1% risk money management system was added… The system had a [trade success] reliability of 38%, which is about average for a trend-following system.

Source: Tharp V, Trade Your Way to Financial Freedom
www.ultimate-trading-systems.com/tywtff
*/

/*********************************
*
*	20111211 KF Tharp strategy
*
*	Using the 10 day exponential
*	MA of the average true range
*	find the initial stop price.
*
*	With a coin flip decide if
*	to enter the trade or not
*
*	With a 1% money management strategy
*	size the trade
*
*	As the price moves, 
*	adjust the stop price.  Also
*	compare the size of the ATR so
*	that if the EMA shrinks so does the
*	stop price.
*
**********************************/

function calculateATR_EMA10()
{
}

function compareStopPrice()
{
}

function adjustStopPrice()
{
}

function coinToss()
{
	$random = rand(1,10);
	echo "Random: $random\n";
	if( $random > 5 )
	{
		return TRUE;
	}
	else
		return FALSE;
}


function tharp()
{
	//return the symbols, stop price deltas
}

if( TRUE == coinToss() )
	echo "TRUE\n";
else
	echo "False\n";
?>

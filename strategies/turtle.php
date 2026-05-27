<?php

echo __FILE__ . "\n";
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
require_once( 'strategiesConstants.php' );


require_once( '../model/stockprices.class.php' );
        $stockprices = new stockprices();



function enter_1( $symbol, $date )
{
        require_once( '../model/stockprices.class.php' );
        $stockprices = new stockprices();
                        $stockprices->Setsymbol( $symbol );
                        $stockprices->Setdate( $date );
                        $stockprices->setValues();
                        $close = $stockprices->Getday_close();
                        if( $close < 0.01 )
                              return FALSE; //see above re no data.
                        $high20 = floor( $this->highprice20() );
                        $low20 = ceil( $this->lowprice20() );
        if ( $close > $high20 )
        {
                return BUY;
        }
        else if ( $close < $low20 )
        {
                return SHORT;
        }
        else
	{
        	return HOLD;
	}
}
function enter_2( $symbol, $date )
{
        require_once( '../model/stockprices.class.php' );
        $stockprices = new stockprices();
                        $stockprices->Setsymbol( $symbol );
                        $stockprices->Setdate( $date );
                        $stockprices->setValues();
                        $close = $stockprices->Getday_close();
                        if( $close < 0.01 )
                              return FALSE; //see above re no data.
                        $high55 = floor( $this->highprice55() );
                        $low55 = ceil( $this->lowprice55() );
        if ( $close > $high20 )
        {
                return BUY;
        }
        else if ( $close < $low55 )
        {
                return SHORT;
        }
        else
	{
        	return HOLD;
	}
}
function exit_1( $symbol, $date )
{
/*
System 1 exit - at a 10 day low for a long trade.  All units sold if there is a 10 day breakout against.

By holding on until the 10/20 day low, you ensure you've ridden the trend to the top and it is starting to come down.
*/

        require_once( '../model/stockprices.class.php' );
        $stockprices = new stockprices();
                        $stockprices->Setsymbol( $symbol );
                        $stockprices->Setdate( $date );
                        $stockprices->setValues();
                        $close = $stockprices->Getday_close();
                        if( $close < 0.01 )
                              return FALSE; //see above re no data.
                        $low10 = ceil( $this->lowprice10() );
                        $high10 = floor( $this->highprice10() );
        if ( $close < $low10 )
        {
                return SELL;
        }
        else if ( $close > $high10 )
        {
                return COVER;
        }
        else
	{
        	return HOLD;
	}
}
function exit_2( $symbol, $date )
{
/*
system 2 exit - at a 20 day low for a long trade.   All units sold if there is a 20 day breakout against.

By holding on until the 10/20 day low, you ensure you've ridden the trend to the top and it is starting to come down.
*/
        require_once( '../model/stockprices.class.php' );
        $stockprices = new stockprices();
                        $stockprices->Setsymbol( $symbol );
                        $stockprices->Setdate( $date );
                        $stockprices->setValues();
                        $close = $stockprices->Getday_close();
                        if( $close < 0.01 )
                              return FALSE; //see above re no data.
                        $low20 = ceil( $this->lowprice20() );
                        $high20 = floor( $this->highprice20() );
        if ( $close < $low20 )
        {
                return SELL;
        }
        else if ( $close > $high20 )
        {
                return COVER;
        }
        else
	{
        	return HOLD;
	}
}

function turtle-system2( $symbol, $date )
{
/* 	System 2
	If a 55 day breakout occurs, take the appropriate buy/sell action.
*/
	$result = enter_2( $symbol, $date );
	if( ( BUY == $result ) OR ( SHORT == $result ) )
	{
		return $result;
	}
	else 
	{
		$result = exit_2( $symbol, $date );
		if( ( SELL == $result ) OR ( COVER == $result ) )
		{
			return $result;
		}
	}
	else
		return HOLD;
}
function turtle-system1( $symbol, $date )
{
	$result = enter_1( $symbol, $date );
	if( ( BUY == $result ) OR ( SHORT == $result ) )
	{
		return $result;
	}
	else 
	{
		$result = exit_1( $symbol, $date );
		if( ( SELL == $result ) OR ( COVER == $result ) )
		{
			return $result;
		}
	}
	else
		return HOLD;
}

function turtle-system($symbol, $date, $system = "BOTH" )
{
/*
*	The turtles used a very simple system:
*	they traded either 1, 2, or 50% 1 + 50% 2:
*	1 - 20 day breakout
*	2 - 55 day breakout.
*/
	if( "BOTH" == $system )
	{
		$t1 = turtle-system1( $symbol, $date );
		$t2 = turtle-system2( $symbol, $date );

		if( $t1 == $t2 )
			return $t1;
		if( HOLD == $t1 )
			return $t2;  //BUY, SELL, COVER, SHORT
		if( HOLD == $t2 )
			return $t1;  //BUY, SELL, COVER, SHORT
	}
	else
	if( "ONE" == $system )
	{
		return turtle-system1( $symbol, $date );
	}
	else
	if( "TWO" == $system )
	{
		return turtle-system2( $symbol, $date );
	}
}

function turtle( $symbol, $date )
{
//Most breakouts do not result in trends.  Therefore entering on breakouts results in a high number of loser trades.
	$action = turtle-system( $symbol, $date, "BOTH" );
	/*If we don't have any of the symbol, we can
	*	BUY, 
	*	SHORT (SELL) or 
	*	HOLD (do nothing)
	/*If we own the symbol, we can 
	*	ADD, ((BUY) check for N and 1/2N values)
	*	HOLD or 
	*	SELL.  
	*	SHORT becomes SELL (should not be a possible case).
	*	COVER isn't possible because we aren't short, but would become BUY
	*	STOP OUT
	*/
	/*If we have shorted the symbol, we can
	*	COVER (BUY), 
	*	SHORT (ADD to the position (SELL)) or 
	*	HOLD (do nothing)
	*	STOP OUT
	*/
	
}

function ADD()
{
/*
ADDING TO A POSITION
If the price moves 1/2N past the breakout, add a unit.  This 1/2N interval is based upon the fill price of the previous order.  If the price slips 1/2N, then the new fill price is 1N above the breakout price. This continues up to the Unit Maximum rule.

i.e.  	N = 2.50 	55 day breakout = 310

1st	2nd	3rd	4th
310	311.25	312.5	313.75
*/
}

function STOP()
{
//Have a predefined stop loss point before entering the position.
//Turtles weren't allowed to risk more than 2%.  Since 1 N = 1%, this is 2N.
//As more units were added, the stop was adjusted to minimize loss
}

function LiquidityCheck( $symbol, $date )
{
/*
What market(s) to trade.
Trading too few reduces your odds of getting ahead of a trend
You also don't want to trade markets that have too low a volume.

Trade only very liquid markets (stocks).  Trading in too small liquidity markets
means that any large purchases by yourself drives the price a great deal but the price will 
return to its norms, so you end up paying too much.  Same principle on the sell

Also, trade markets consistently.  If you aren't going to trade oil company shares,
then NEVER trade oil company shares.  Inconsistency hurts in the long run as you
end up trading on emotion rather than on your system.
*/
}

/*


System 1

For the 20 day system, the signal was ignored if the last breakout would have resulted in a winning trade (appears they had a fixed 10 day sale).  It didn't matter if the previous breakout was taken or skipped, nor the direction of the breakout.  The breakout was considered a LOSING trade if it moved 2N against the position before the 10 day exit.  Because of this skip, the *fallback* breakout point is now the 55 day, for this 1 time only to ensure a major move isn't missed out on.

If you are out of the market, there will always be a price which triggers a short and another higher price which triggers a long.  If the breakout was a loser, the entry would be closer to the current price (i.e. 20 day) then had it been a winner in which case the entry signal was farther away (i.e. 55 day).



Exit is pre-determining at what point to get out of a trade.
Taking a profit too early is the most common mistake.



See turtle-entry for definition of N

Have a predefined stop loss point before entering the position.
Turtles weren't allowed to risk more than 2%.  Since 1 N = 1%, this is 2N.
As more units were added, the stop was adjusted to minimize loss

N = 1.2
55 breakout = 28.30
Unit	Entry	Stop
1st	28.30	25.90

1st	28.30	25.90 => 26.5
2nd	28,90	26.50

1	28.30	25.90 => 26.5 => 27.10
2	28.90	26.50 => 27.10
3	29.5	27.10

ALTERNATIVE METHOD - WHIPSAW
Has more losers but better long term profitability

Instead of 2% risk, place stops at 1/2N (1/2% risk)
If a unit is stopped out, the unit would be re-entered if the market reached the original entry price.
Also doesn't adjust the stops of earlier units since the maximum risk is still less than 2%.


N = 1.2
55 breakout = 28.30
Unit	Entry	Stop
1st	28.30	27.70

1st	28.30	27.70
2nd	28,90	28.30

1	28.30	27.70
2	28.90	28.30
3	29.5	28.90

Since the stops are based on N, they adjust for market volatility:
Larger volatility is larger N, but lower number of contracts, so #contract * N = constant.


Use limit orders, not market orders.  Ensures a more guaranteed price reducing slip.

In fast moving markets, wait until the price stabilizes before placing the limit order.
Limit orders don't influence the market.
On price bounces (random moves) place the limit at the bottom of the bounce.

Buy strength, Sell Weakness

If a bunch of signals come all at once, buy the strongest market and sell the weakest.  This also considers volume and liquidity.

One way of determining strength is to determing how many N the price has moved since the breakout, and buy the market with the most N.

Another to normalize markets: (Current price - close90) / CurrentN  
Stronger have higher values




*/

?>

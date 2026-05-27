/*
::::::::::::::
Close/BreakEven
::::::::::::::


Prevent a winning trade from becoming a losing trade.

Once a target price has been reached, set a stop loss order.
Calculate the stop loss price based upon trade fees, etc
::::::::::::::
Close/Channel
::::::::::::::
A Channel is when you have both a short and a long position

This Channel Breakout exit strategy close a position once the lower level
has been triggered for a long position, as well as the upper level for a
short position.

::::::::::::::
Close/CloseLong
::::::::::::::


Close a long position once the price has crossed X%
::::::::::::::
Close/CloseShort
::::::::::::::


Close a short position when the price has crossed X% 
::::::::::::::
Close/KeepRun
::::::::::::::


Once the price has hit a high (low) and has reversed, send the Close signal once the price crosses a threshold
(i.e. 10%) change from that high.  Ie the price hits 10 and starts falling.  Sell at 9 dollars.
::::::::::::::
Close/LimitedTime
::::::::::::::


Close a position after having owned the share/short for X days
::::::::::::::
Close/NeverClose
::::::::::::::


Never close the position.  Used for Buy and Hold or Sell and Hold.
::::::::::::::
Close/OppositeSIgnal
::::::::::::::


Close a short on a stock if a BUY signal is recieved for that same stock

sell a stock if a SHORT signal is recieved for that same stock
::::::::::::::
Close/PartialClose
::::::::::::::


Close a portion of the position (i.e. 50% of the position) once a defined part of the target has been reached (i.e. 50% of the target)
::::::::::::::
Close/Target
::::::::::::::


Close a gain once the share price has crossed a target price:

::::::::::::::
Close/ValueAtRisk
::::::::::::::

This method uses market volatility and the concept of value at risk (VAR)
to help determine meaningful stop-loss prices and position limits for
trading securities.

*/

//Below are ones that can't be moved into the class.
function calcCloseChannel( $symbol, $date )
{
	return FALSE;
}
function calcCloseRun( $symbol, $date )
{
	return FALSE;
}
function calcCloseOppositeSignal( $symbol, $date )
{
	return FALSE;
}
function calcCloseValueAtRisk( $symbol, $date )
{
	return FALSE;
}




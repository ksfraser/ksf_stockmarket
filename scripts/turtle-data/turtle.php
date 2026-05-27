<?php

require_once( $MODELDIR . "/stockprices.class.php" );
require_once( $MODELDIR . "/turtledata.class.php" );


class turtle extends turtledata
{
	var $volatility1;
	var $high0;
	var $low0;
	var $high1;
	var $close1;

	function turtle( $stock, $date )
	{
		$this->symbol = $stock;
		$this->date = $date;
		$this->getprereqs();
		$this->calcturtle();
		$this->InsertVAR();
		return;
	}
	
	function calcturtle()
	{
/*
		$this->breakouthigh55 = $this->breakouthigh55();
		$this->breakouthigh20 = $this->breakouthigh20();
		$this->breakoutlow55 = $this->breakoutlow55();
		$this->breakoutlow20 = $this->breakoutlow20();
		$this->high10 = $this->high10();
		$this->high20 = $this->high20();
		$this->low10 = $this->low10();
		$this->low20 = $this->low20();
		$this->calctruerange();
		$this->calcvolatility();
		$this->calcunit();
		$this->calcpositionadd();
		$this->calcsellallprice();
		$this->calcnormalizedprice();
		$this->calcignore20();
*/
		$this->calculateturtledata();
		return;
	}

	function breakouthigh( $days )
	{
		$days = round( $days * 7 / 5 );
		$stockprices = new stockprices();
		$stockprices->select = "max( day_close ) as breakout";
		$stockprices->where = "symbol = '" . $this->stock . "' and date >= DATE_SUB( '" . $this->date . "', INTERVAL " . $days . " DAY  )";
		$stockprices->Select();
		$results = $stockprices->resultarray[0]['breakout'];
		unset( $stockprices );
		return $results;
	}
	
	function breakouthigh20( )
	{
		return breakouthigh( 20 );
	}
	
	function breakouthigh55( )
	{
		return breakouthigh( 55 );
	}
	
	function breakoutlow($days )
	{
		$days = round( $days * 7 / 5 );
		$stockprices = new stockprices();
		$stockprices->select = "min( day_close ) as breakout";
		$stockprices->where = "symbol = '" . $this->stock . "' and date >= DATE_SUB( '" . $this->date . "', INTERVAL " . $days . " DAY  )";
		$stockprices->Select();
		$results = $stockprices->resultarray[0]['breakout'];
		unset( $stockprices );
		return $results;
	}
	
	function breakoutlow20()
	{
		return breakoutlow();
	}
	
	function breakoutlow55()
	{
		return breakoutlow( $stock, $date, 55 );
	}

	function high( $days )
	{
		$days = round( $days * 7 / 5 );
		$stockprices = new stockprices();
		$stockprices->select = "max( day_close ) as ";
		$stockprices->where = "symbol = '" . $this->stock . "' and date >= DATE_SUB( '" . $this->date . "', INTERVAL " . $days . " DAY  )";
		$stockprices->Select();
		$results = $stockprices->resultarray[0][''];
		unset( $stockprices );
		return $results;
	}
	
	function high20( )
	{
		return high( 20 );
	}
	
	function high10( )
	{
		return high( 10 );
	}
	
	function low($days )
	{
		$days = round( $days * 7 / 5 );
		$stockprices = new stockprices();
		$stockprices->select = "min( day_close ) as ";
		$stockprices->where = "symbol = '" . $this->stock . "' and date >= DATE_SUB( '" . $this->date . "', INTERVAL " . $days . " DAY  )";
		$stockprices->Select();
		$results = $stockprices->resultarray[0][''];
		unset( $stockprices );
		return $results;
	}
	
	function low20()
	{
		return low( 20 );
	}
	
	function low10()
	{
		return low( 10 );
	}

	function getprereqs()
	{
		$stockprices = new stockprices();
	/*
		$stockprices->setdate( $this->getdate );
		$stockprices->setstocksymbol( $this->getsymbol );
		$stockprices->GetVARRow();
		$this->sethigh0( $stockprices->getday_high() );
	 	$this->setlow0( $stockprices->getday_low() );

	*/
		$stockprices->select = "day_low, day_high";
		$stockprices->where = " date = '" . $this->date . "'" . " and symbol = '" . $this->symbol . "'";
		$stockprices->Select();
		$this->high0 = $stockprices->resultarray[0]['day_high'];
		$this->low0 = $stockprices->resultarray[0]['day_low'];

		$stockprices->select = "day_close, day_high, max( date ) as date1";
		$stockprices->where = " date1 < '" . $this->date . "'" . " and symbol = '" . $this->symbol . "'";
		$stockprices->Select();
		$this->high1 = $stockprices->resultarray[0]['day_high'];
		$this->close1 = $stockprices->resultarray[0]['day_close'];
		$date1 = $stockprices->resultarray[0]['date1'];

		unset( $stockprices );

		$this->select = "volatility";
		$this->where = "date = '" . $date1 . "'";
		$this->Select();
		$this->volatility1 = $this->resultarray[0]['volatility'];
		return;
	}
}

?>

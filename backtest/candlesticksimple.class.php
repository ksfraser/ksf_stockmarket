<?php

//20111227 KF
//Testing framework.  All strategies have common actions so consolidating these into a class

require_once( '../model/include_all.php' );
require_once( 'backtest.class.php' );


class candlesticksimple extends backtest
{
	var $actionarray; //array of actions to take on a candlestick
	var $cso_c; //candlestickoccured class
	function __construct( $username = "candlestick_simple", $startingcash = "10000", $symbol = "IBM", $startdate = "2011-01-02", $enddate = "2011-12-25", $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE" )
	{
		require_once( MODELDIR . '/candlesticksoccured.class.php' );
		$this->cso_c = new candlesticksoccured();

		parent::__construct( $username, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
		require_once( MODELDIR . '/candlestickactions.class.php' );
		$csa = new candlestickactions();
		$this->actionarray = $csa->Getactionarray();
		$this->Setbuystockaverage( "60" );
		$this->Setsellstockaverage( "40" );

	}
	function Settransactiondate( $date )
	{
		parent::Settransactiondate( $date );
		$this->cso_c->Setdate( $date );
	}
	function Setsymbol( $symbol )
	{
		parent::Setsymbol( $symbol );
		$this->cso_c->Setsymbol( $symbol );
	}
	function SellStrategy()
	{
		$this->cso_c->GetVARArray();
		$count = 0;
		$total = 0;
		foreach( $this->cso_c->resultarray as $row )
		{
			//List of candlesticks on that date for that symbol
			$total = $total + $this->actionarray[ $row['candlestick'] ]['candlestick_action_value'];
			$count++;
	
			$this->Log( "Candlestick " . $this->actionarray[ $row['candlestick']]['candlestick_name'] . " has action " . $this->actionarray[ $row['candlestick']]['candlestick_action'] . " and VALUE  " . $this->actionarray[ $row['candlestick'] ]['candlestick_action_value'] );
		}
		if( $count > 0 )
		{
			$average = $total / $count;
			$this->Log( $count . " candlesticks with a total of " . $total . " for average " . $average );
			if( $average > $this->Getbuystockaverage() )
				$this->Setaction( "buystock" );
			else
			if( $average < $this->Getsellstockaverage() )
				$this->Setaction( "sellstock" );
			else
				$this->Setaction( "None" );
		}
	}
	function BuyStrategy()
	{
		//This is covered in SellStrategy due to the nature of the data storage
		return NULL;
	}
}
/*
function testcandlesticksimple( $symbol, $startingcash, $startdate, $enddate )
{
	//go through technical analysis for this symbol,
	//using the identified candlesticks sell or buy
	//ALL stocks or all cash.
	//
	//DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
		$user = "candlestick_simple";
		$firstname = "Candlestick";
		$lastname = "Simple";
		$email = "fraser.ks@gmail.com";
		$currency = "CAD"; 
		$foreigncurrency = "CAD"; 
		$account = "TRADE";
	$candlesticksimple = new candlesticksimple( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
	$candlesticksimple->AddUser( $firstname, $lastname, $email );
	$candlesticksimple->RunStrategy();
return SUCCESS;
}


//TESTING
//build tradedatearray
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
testcandlesticksimple( $symbol, $startingcash, $startdate, $enddate );
*/
/*
*/
?>

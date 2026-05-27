<?php

//20111227 KF
//Testing framework.  All strategies have common actions so consolidating these into a class

require_once( '../model/include_all.php' );
require_once( 'backtest.class.php' );


class buyhold extends backtest
{
	var $boughtonce = 0;
	function SellStrategy()
	{
		if( $this->Gettransactiondate() >= $this->Getenddate() )
			$this->Setaction( "sellstock" );
		else
			$this->Setaction( "None" );
	}
	function BuyStrategy()
	{
		//if( $this->Gettransactiondate() <= $this->Getstartdate() )
		if( $this->boughtonce < 10 )
		{
			$this->Setaction( "buystock" );
			$this->boughtonce++;
		}
		else
			$this->Setaction( "None" );
	}
}
?>

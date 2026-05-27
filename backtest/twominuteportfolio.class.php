<?php

/*
*	The 2 minute portfolio uses the top 2 by market cap dividend paying stocks in each of the 10 Cdn financial sectors.
*	This portfolio is rebalanced once a year.  You invest equally in each of these 20 stocks.
*/

require_once( '../model/include_all.php' );
require_once( 'backtest.class.php' );


class twominuteportfolio_stock extends backtest
{
	//This class will handle the stock by stock part of the 2 minute portfolio strategy
        var $boughtonce = 0;
	var $stockinfo_c;
	function __construct( $username = "twominute_portfolio", $startingcash = "10000", $symbol = "IBM", $startdate = "2011-01-02", $enddate = "2011-12-25", $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE", $numbersymbolssharedollars = "20" )
        {
		echo "2m_stock construct\n";
                require_once( MODELDIR . '/stockinfo.class.php' );
                $this->stockinfo_c = new stockinfo();

		echo "2m_stock construct CALLING parent\n";
                parent::__construct( $username, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account, $numbersymbolssharedollars );
		echo "2m_stock construct RETURN from parent\n";
        }
	function Setsymbol( $symbol )
        {
                parent::Setsymbol( $symbol );
                $this->stockinfo_c->Setstocksymbol( $symbol );
        }
        function SellStrategy()
        {
		//Sell if no longer one of the top 2 in the sector
                //if( !$stockinfo->DividendByMarketcap( $this->Getsymbol() ) )
		
                if( $this->Gettransactiondate() >= $this->Getenddate() )
                        $this->Setaction( "sellstock" );
                else
                        $this->Setaction( "None" );
        }
        function BuyStrategy()
        {
		//Buy if one of the top 2 in the sector
                //if( $stockinfo->DividendByMarketcap( $this->Getsymbol() ) )
                if( $this->Gettransactiondate() <= $this->Getstartdate() )
                {
                        $this->Setaction( "buystock" );
                }
                else
                        $this->Setaction( "None" );
        }

}

class twominuteportfolio extends twominuteportfolio_stock
//class twominuteportfolio 
{
	//This class will store the portfolio for this approach
	//handling the portfolio approach of the 20 stocks (2*10 sectors)
	var $currentportfoliolist = array(); //array of stocks currently in the portfolio
	var $futureportfoliolist = array(); //array of stocks to rebalance into the portfolio
	var $symbolobjectarray = array(); //Array of twominuteportfolio_stock objects
	
	//stockinfo has fields annualdividendpershare, marketcap, idstocksector

	function __construct($username = "twominute_portfolio", $startingcash = "10000", $symbol = "IBM", $startdate = "2011-01-02", $enddate = "2011-12-25", $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE", $numbersymbolssharedollars = "20" )
	{
		echo "Construct \n";
		$username = "twominute_portfolio"; 
		$startingcash = "10000"; 
		$symbollist = array( "IBM", "DELL" );
		$numbersymbolssharedollars = count( $symbollist);
		
		$startdate = "2011-01-02"; 
		$enddate = "2011-12-25"; 
		$currency = "CAD"; 
		$foreigncurrency = "CAD"; 
		$account = "TRADE"; 
		foreach( $symbollist as $symbol )
		{
			echo "Create array for $symbol\n";
			$this->currentportfoliolist[$symbol] = new twominuteportfolio_stock( $username, $startingcash / $numbersymbolssharedollars, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account, $numbersymbolssharedollars );
			echo "Array created for $symbol\n";
		}
		echo "AddUser\n";
		$this->AddUser( "Two Minute", "Portfolio", "fraser.ks@gmail.com" );
		echo "Run";
		$this->RunStrategy();
		echo "End\n";
	}
//	function RunStrategy()
//	{
//	}
}
$username = "twominute_portfolio"; $startingcash = "10000"; $symbol = "IBM"; $startdate = "2011-01-02"; $enddate = "2011-12-25"; $currency = "CAD"; $foreigncurrency = "CAD"; $account = "TRADE"; $numbersymbolssharedollars = "20" ;
$test = new twominuteportfolio($username, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account, $numbersymbolssharedollars );



?>

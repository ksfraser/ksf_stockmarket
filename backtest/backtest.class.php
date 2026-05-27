<?php

//20111227 KF
//Testing framework.  All strategies have common actions so consolidating these into a class

require_once( '../model/include_all.php' );
//require_once( '../strategies/strategiesConstants.php' );  //Moved into local.php
require_once( 'Log.php' );

/*
$console = Log::factory('console', '', 'TEST');
$console->log('Logging to the console.');

$file = Log::factory('file', 'out.log', 'TEST');
$file->log('Logging to out.log.');
*/


class backtest
{
	var $user; //The username of the test user
	var $cash; //How much cash we have
	var $flog; //Log File pointer
	var $logger; //PEAR Log handler
	var $symbol; //The stock symbol under consideration
	var $transactiondate;
	var $startdate;
	var $enddate;
	var $currency;
	var $foreigncurrency; //Someday transactions will handle exchange rates, etc
	var $numbershares; //how many to buy/sell this transaction
	var $account;
	var $sharecost; //Cost of the shares on a given date
	var $transactiondollars; //Dollars to spend on the transaction
	var $action; //Action to take - buy or sell
	var $portfolio_marketvalue; //Users marketvalue for the portfolio
	var $portfolio_bookvalue; //Users bookvalue for the portfolio
	var $maxsingletrade; //Percentage maximum of book/market value to trade in 1 transaction
	var $maxrisk; //Pct max risk
	var $dollars2risk;
	var $dollars2invest; //Adjusted for max per trade...
	var $float; //How much to invest on 1 transaction adjusted
	var $endcash; //the final cash value on the end date
	var $startcash; //the starting cash
	var $lastaction; //The last action - buy or sell
	var $buybookvalue; //Total of all buys before a sell
	var $transactionsets; // how many buy - sell sets
	var $winratio;	//how many buy sell sets are a win
	var $loseratio; //how many buy sell sets are a lose
	var $successratio; //win/lose
	var $winsize;
	var $losesize;
	var $expectancy; //size of wins*%win subtract size of loss*%loss
	var $initialstopsize;
	var $truerangefactor; //Number of days ATR for initial stop
	var $symbolheat; //The heat of this particular symbol within the portfolio
	var $heatbuycount;
	var $numbersymbolssharedollars; //Number of symbols upon which a dollar amount must be shared.
	var $buystockaverage; //For strategies that need an average value trigger
	var $sellstockaverage; //For strategies that need an average value trigger
	var $transaction_c; //Transaction class for performing stock transactions
	var $transaction_close_c; //Transaction_close class for performing stock transactions
	var $ta_c; //Technical Analysis class
	var $stockprices_c; //Stock Prices class
	var $portfolio_c;
	var $userpref_c;
	function __construct( $username = "backtest", $startingcash = "10000", $symbol = "IBM", $startdate = "2011-01-02", $enddate = "2011-12-25", $currency = "CAD", $foreigncurrency = "CAD", $account = "TRADE", $numbersymbolssharedollars = "1" )
	{
		//ob_start();
		echo __FILE__ . " construct\n";
	        require_once( MODELDIR . '/userpref.class.php' );
		echo __FILE__ . " construct userpref\n";
	        $this->userpref_c = new userpref();
		require_once( '../model/transaction.class.php' );
		echo __FILE__ . " construct transaction\n";
		$this->transaction_c = new transaction();
		require_once( '../model/technicalanalysis.class.php' );
		echo __FILE__ . " construct technicalanalysis\n";
		$this->ta_c = new technicalanalysis();
		require_once( '../model/stockprices.class.php' );
		echo __FILE__ . " construct stockprices\n";
		$this->stockprices_c = new stockprices();
	        require_once( MODELDIR . '/portfolio.class.php' );
		echo __FILE__ . " construct portfolio\n";
	        $this->portfolio_c = new portfolio();
		require_once( '../model/transaction_close.class.php' );
		echo __FILE__ . " construct transaction_close\n";
		$this->transaction_close_c = new transaction_close();
		echo __FILE__ . " Set user\n";

		$this->Setuser( $username );
		echo __FILE__ . " Create logger\n";

		$logfile = LOGDIR . '/' . $username . "." . date( 'YmdHis' ) . ".txt";
		$this->flog = fopen( $logfile, "w" );
		$this->logger = Log::factory('file', $logfile, 'BACKTEST');
		$pref = $this->userpref_c->RetrievePref( $this->Getuser(), "Log_Default_Level" );
                if( isset( $pref ))
                {
                        $logMin = $pref;
                }
                else
                {
			$logMin = Backtest_Log_Default_Level;
			$logMin = PEAR_LOG_NOTICE;
                }
		$this->logger->setMask( Log::MIN( $logMin ) );
		//$this->logger->setMask( Log::MIN( Backtest_Log_Default_Level ) );
		$this->Log_INFO( "Created logfile at " . date( 'YmdHis' ) );

		echo __FILE__ . " Set initial values\n";

		$this->Setcash( $startingcash );
		$this->Setstartcash( $startingcash );
		$this->Setsymbol( $symbol );
		$this->Settransactiondate( $startdate ); 
		$this->Setstartdate( $startdate );
		$this->Setenddate( $enddate );
		$this->Setcurrency( $currency );
		$this->Setforeigncurrency( $currency );
		$this->Setaccount( $account );
		$this->Setnumbershares( 0 );
		$this->Setsharecost( 0 );
		$this->Settransactiondollars( 0 );
	        $this->Setportfolio_marketvalue( 0 );
	        $this->Setportfolio_bookvalue( 0 );
	        $this->Setbuybookvalue( 0 );
	        $this->Setwinratio( 0 );
	        $this->Setloseratio( 0 );
	        $this->Setwinsize( 0 );
	        $this->Setlosesize( 0 );
	        $this->Setsymbolheat( 0 );
		$this->Setexpectancy( 0 );
	        $this->Setsuccessratio( 0 );
	        $this->Settransactionsets( 0 );
	        $this->Setnumbersymbolssharedollars( $numbersymbolssharedollars );
	        $this->Setlastaction( "" );
		echo __FILE__ . " RETURN from construct\n";
	}
	function Getmaxsingletrade()
	{
		if( !isset( $this->maxsingletrade ) OR ( 0 == $this->maxsingletrade ) )
			$this->Calcmaxsingletrade();
		return $this->maxsingletrade;
	}
	function Setmaxsingletrade( $maxsingletrade )
	{
		$this->maxsingletrade = $maxsingletrade;
	}
	function Gettransactiondollars()
	{
		return $this->transactiondollars;
	}
	function Settransactiondollars( $transactiondollars )
	{
		$this->transactiondollars = $transactiondollars;
	}
	function Getnumbersymbolssharedollars()
	{
		return $this->numbersymbolssharedollars;
	}
	function Setnumbersymbolssharedollars( $numbersymbolssharedollars )
	{
		$this->numbersymbolssharedollars = $numbersymbolssharedollars;
		$this->Log( "Setting Symbol Heat to " . $numbersymbolssharedollars );
	}
	function Getbuystockaverage()
	{
		return $this->buystockaverage;
	}
	function Setbuystockaverage( $buystockaverage )
	{
		$this->buystockaverage = $buystockaverage;
		$this->Log( "Setting Symbol Heat to " . $buystockaverage );
	}
	function Getsellstockaverage()
	{
		return $this->sellstockaverage;
	}
	function Setsellstockaverage( $sellstockaverage )
	{
		$this->sellstockaverage = $sellstockaverage;
		$this->Log( "Setting Symbol Heat to " . $sellstockaverage );
	}
	function Getheatbuycount()
	{
		return $this->heatbuycount;
	}
	function Setheatbuycount( $heatbuycount )
	{
		$this->heatbuycount = $heatbuycount;
		$this->Log( "Setting Symbol Heat to " . $heatbuycount );
	}
	function Getsymbolheat()
	{
		return $this->symbolheat;
	}
	function Setsymbolheat( $symbolheat )
	{
		$this->symbolheat = $symbolheat;
		$this->Log( "Setting Symbol Heat to " . $symbolheat );
	}
	function Getexpectancy()
	{
		return $this->expectancy;
	}
	function Setexpectancy( $expectancy )
	{
		$this->expectancy = $expectancy;
		$this->Log( "Setting expectancy to " . $expectancy );
	}
	function Getinitialstopsize()
	{
		return $this->initialstopsize;
	}
	function Setinitialstopsize( $initialstopsize )
	{
		$this->initialstopsize = $initialstopsize;
		$this->transaction_close_c->Setstopsize( $initialstopsize );
		$this->Log( "Setting initialstopsize to " . $initialstopsize );
	}
	function Getwinsize()
	{
		return $this->winsize;
	}
	function Setwinsize( $winsize )
	{
		$this->winsize = $winsize;
		$this->Log( "Setting winsize to " . $winsize );
	}
	function Getlosesize()
	{
		return $this->losesize;
	}
	function Setlosesize( $losesize )
	{
		$this->losesize = $losesize;
		$this->Log( "Setting losesize to " . $losesize );
	}
	function Getlastaction()
	{
		return $this->lastaction;
	}
	function Setlastaction( $lastaction )
	{
		$this->lastaction = $lastaction;
		$this->Log( "Setting lastaction to " . $lastaction );
	}
	function Getbuybookvalue()
	{
		return $this->buybookvalue;
	}
	function Setbuybookvalue( $buybookvalue )
	{
		$this->buybookvalue = $buybookvalue;
		$this->Log( "Setting buybookvalue to " . $buybookvalue );
	}
	function Gettransactionsets()
	{
		return $this->transactionsets;
	}
	function Settransactionsets( $transactionsets )
	{
		$this->transactionsets = $transactionsets;
		$this->Log( "Setting transactionsets to " . $transactionsets );
	}
	function Getwinratio()
	{
		return $this->winratio;
	}
	function Setwinratio( $winratio )
	{
		$this->winratio = $winratio;
		$this->Log( "Setting winratio to " . $winratio );
	}
	function Getloseratio()
	{
		return $this->loseratio;
	}
	function Setloseratio( $loseratio )
	{
		$this->loseratio = $loseratio;
		$this->Log( "Setting loseratio to " . $loseratio );
	}
	function Getsuccessratio()
	{
		return $this->successratio;
	}
	function Setsuccessratio( $successratio )
	{
		$this->successratio = $successratio;
		$this->Log( "Setting successratio to " . $successratio );
	}
	function Getstartcash()
	{
		return $this->startcash;
	}
	function Setstartcash( $startcash )
	{
		$this->startcash = $startcash;
		$this->Log( "Setting startcash to " . $startcash );
	}
	function Getendcash()
	{
		return $this->endcash;
	}
	function Setendcash( $endcash )
	{
		$this->endcash = $endcash;
		$this->Log( "Setting endcash to " . $endcash );
	}
	function Getfloat()
	{
		return $this->float;
	}
	function Setfloat( $float )
	{
		$this->float = $float;
		$this->Log( "Setting float to " . $float );
	}
	function Getdollars2invest()
	{
		return $this->dollars2invest;
	}
	function Setdollars2invest( $dollars2invest )
	{
		$this->dollars2invest = $dollars2invest;
		$this->Log( "Setting dollars2invest to " . $dollars2invest );
	}
	function Getdollars2risk()
	{
		return $this->dollars2risk;
	}
	function Setdollars2risk( $dollars2risk )
	{
		$this->dollars2risk = $dollars2risk;
		$this->Log( "Setting dollars2risk to " . $dollars2risk );
	}
	function Getmaxrisk()
	{
		return $this->maxrisk;
	}
	function Setmaxrisk( $maxrisk )
	{
		$this->maxrisk = $maxrisk;
		$this->Log( "Setting maxrisk to " . $maxrisk );
	}
	function Getaction()
	{
		return $this->action;
	}
	function Setaction( $action )
	{
		$this->action = $action;
		$this->Log( "Setting action to " . $action );
	}
	function Getportfolio_marketvalue()
	{
		return $this->portfolio_marketvalue;
	}
	function Setportfolio_marketvalue( $portfolio_marketvalue )
	{
		$this->portfolio_marketvalue = $portfolio_marketvalue;
	}
	function Getportfolio_bookvalue()
	{
		return $this->portfolio_bookvalue;
	}
	function Setportfolio_bookvalue( $portfolio_bookvalue )
	{
		$this->portfolio_bookvalue = $portfolio_bookvalue;
	}
	function Getforeigncurrency()
	{
		return $this->foreigncurrency;
	}
	function Setforeigncurrency( $foreigncurrency )
	{
		$this->foreigncurrency = $foreigncurrency;
	}
	function Getaccount()
	{
		return $this->account;
	}
	function Setaccount( $account )
	{
		$this->account = $account;
		$this->transaction_c->Setaccount( $account );
		$this->transaction_close_c->Setaccount( $account );
		$this->portfolio_c->Setaccount( $account );
		$this->Setportfolio_marketvalue( 0 ); //Changing accounts makes these values stale
		$this->Setportfolio_bookvalue( 0 );
		$_SESSION['account'] = $account;
	}
	function Getcurrency()
	{
		return $this->currency;
	}
	function Setcurrency( $currency )
	{
		$this->currency = $currency;
		$this->transaction_c->Setcurrency( $currency );
		$this->transaction_close_c->Setcurrency( $currency );
	}
	function Setstartdate( $startdate )
	{
		$this->startdate = $startdate;
		$this->Log( "Setting startdate to " . $startdate );
	}
	function Getstartdate()
	{
		return $this->startdate;
	}
	function Setenddate( $enddate )
	{
		$this->enddate = $enddate;
		$this->Log( "Setting enddate to " . $enddate );
	}
	function Getenddate()
	{
		return $this->enddate;
	}
	function Gettransactiondate()
	{
		return $this->transactiondate;
	}
	function Settransactiondate( $transactiondate )
	{
		$this->transactiondate = $transactiondate;
		$this->transaction_c->Settransactiondate( $transactiondate );
		$this->transaction_close_c->Settransactiondate( $transactiondate );
		$this->ta_c->Setdate( $transactiondate );
		$this->stockprices_c->Setdate( $transactiondate );
		//$this->portfolio_c->Setdate( $transactiondate );
		$this->Log( "Setting transactiondate to " . $transactiondate );
	}
	function Getsymbol()
	{
		return $this->symbol;
	}
	function Setsymbol( $symbol )
	{
		$this->symbol = $symbol;
		$this->transaction_c->Setstocksymbol( $symbol );
		$this->transaction_close_c->Setstocksymbol( $symbol );
		$this->ta_c->Setsymbol( $symbol );
		$this->stockprices_c->Setsymbol( $symbol );
		$this->portfolio_c->Setstocksymbol( $symbol );
		$this->Log( "Setting symbol to " . $symbol );
	}
	function Getcash()
	{
		return $this->cash;
	}
	function Setcash( $cash )
	{
		$this->cash = $cash;
		$this->Log( "Setting cash to " . $cash );
	}
	function Getuser()
	{
		return $this->user;
	}
	function Setuser( $user )
	{
		$this->user = $user;
		$this->portfolio_c->Setusername( $user );
		$this->transaction_c->Setusername( $user );
		$this->transaction_close_c->Setusername( $user );
		$_SESSION['username'] = $user;
	}
	function Log( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_INFO);

	}
	function Log_DEBUG( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_DEBUG);

	}
	function Log_INFO( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_INFO);

	}
	function Log_NOTICE( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_NOTICE);

	}
	function Log_WARNING( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_WARNING);

	}
	function Log_ERR( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_ERR);

	}
	function Log_EMERG( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_EMERG);

	}
	function Log_CRIT( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_CRIT);

	}
	function Log_ALERT( $message )
	{
		//fwrite( $this->flog, $message . "\n" );
		$this->logger->log($message, PEAR_LOG_ALERT);

	}
	function Settruerangefactor( $truerangefactor )
	{
		$this->truerangefactor = $truerangefactor;
		$this->Log( "Setting truerangefactor to " . $truerangefactor );
	}
	function Gettruerangefactor()
	{
		return $this->truerangefactor;
	}
	function Calctruerangefactor()
	{
	        $pref = $this->userpref_c->RetrievePref( $this->Getuser(), "MM_truerangefactor" );
	        if( isset( $pref ))
	        {
	                $truerangefactor = $pref;
	        }
	        else
	 	{
	                $truerangefactor = MM_truerangefactor;
	        }
		$this->Settruerangefactor( $truerangefactor );
	}
	function Setsharecost( $cost )
	{
		$this->sharecost = $cost;
		$this->transaction_close_c->SetcloseBreakEven( $cost );
		$this->Log( "Setting share cost to " . $cost );
	}
	function Getsharecost()
	{
		return $this->sharecost;
	}
	function Calcsharecost()
	{
		//These two are taken care of by THIS's Set*
		//$this->stockprices_c->date = $this->transactiondate;
		//$this->stockprices_c->symbol = $this->symbol;
		$this->ClearStockpricesVAR();
/*
		 $this->stockprices_c->adjustedclose = NULL;
		 $this->stockprices_c->volume = NULL;
		 $this->stockprices_c->day_close = NULL;
		 $this->stockprices_c->day_open = NULL;
		 $this->stockprices_c->day_high = NULL;
		 $this->stockprices_c->day_low = NULL;
*/
		$price = $this->stockprices_c->Getmidprice();
		$this->Log( "Shares for " . $this->stockprices_c->Getsymbol() . " on " . $this->stockprices_c->Getdate() . " cost " . $price . " H/L: " . $this->stockprices_c->Getday_high() . ":" . $this->stockprices_c->Getday_low() );
		$this->Setsharecost( $price );
	}
	function Calcnumbershares()
	{
		// We need to also check the max risk (risksize) number of shares by the stop size so that we aren't risking too much
		//maximum loss / initial stop size  = number of units to purchase.
		if( 0 < $this->Getinitialstopsize() )
			$units = floor( $this->Getdollars2risk() / $this->Getinitialstopsize() );
		else
			$units = 0;
		$floatcost = floor( $this->Getfloat() / $this->Getsharecost() );
		$this->Log( "Purchase " . $floatcost . " units or risk on " . $units . " shares" );
		$this->Setnumbershares( min( $floatcost, $units ) );
	}
	function Getnumbershares()
	{
		return $this->numbershares;
	}
	function Setnumbershares( $numbershares )
	{
		$this->numbershares = $numbershares;
		$this->Log( "Setting number of shares to " . $numbershares );
		$this->transaction_c->Setnumbershares( $numbershares );
		$this->transaction_close_c->Setnumbershares( $numbershares );
	}
	function BuyStock()
	{
		if( $this->Getnumbershares() > 0 )
		{
			$this->Log_NOTICE( "Buy stocks - Shares: " . $this->Getnumbershares() . " for $" . $this->Gettransactiondollars() );
 			$this->transaction_c->useraccountbuystock($this->flog, $this->Getuser(), $this->Getsymbol(), 
					$this->Getnumbershares(), $this->Gettransactiondollars(), $this->Gettransactiondate(), 
					$this->Getcurrency(), $this->Getforeigncurrency(), $this->Getaccount() );
			$this->transaction_close_c->Setdollar( $this->Gettransactiondollars() );
			$this->transaction_close_c->Settransactiontype( "BUY" );
			$this->transaction_close_c->InsertVAR();
			$this->portfolio_c->UpdatePortfolios();
		}
		$this->Setbuybookvalue( $this->Getbuybookvalue() + $this->Gettransactiondollars() );
		$this->Setheatbuycount( $this->Getheatbuycount() + 1 );
		$this->Setsymbolheat( $this->Getbuybookvalue() / ( $this->Getportfolio_marketvalue() + $this->Getcash() ) );

	}
	/*@bool@*/ function ActionBuyStock()
	{
		$this->Log( "Have $" . $this->Getcash() . " with which to buy shares" );
		$this->Calcsharecost();
		if( $this->Getsharecost() == 0 )
		{
			$this->Log_ERR( "Invalid share price.  Can't buy when price 0" );
			return FALSE;
		}
		if ($this->Getcash() > 0)
		{
			if( $this->ReinvestmentStrategy() )
			{
				$this->Calcnumbershares(); //Calcnumbershares assumes risk/dollars are entirely for this symbol whereas the strategy
							//might not allocate all the money to 1, assume that allocation will be even...
				$this->Settransactiondollars( $this->Getnumbershares() * $this->Getsharecost() / $this->Getnumbersymbolssharedollars() );
				$this->BuyStock();
				return TRUE;
			}
			else
				return FALSE;
		} else
		{
			$this->Log_WARN( "Can't buy shares without money" );
			return FALSE;
		}
	}
	function SellStock()
	{
		if( $this->Getnumbershares() > 0 )
		{
 			$this->transaction_c->useraccountsellstock($this->flog, $this->Getuser(), $this->Getsymbol(), 
					$this->Getnumbershares(), $this->Gettransactiondollars(), $this->Gettransactiondate(), 
					$this->Getcurrency(), $this->Getforeigncurrency(), $this->Getaccount() );
			$this->portfolio_c->UpdatePortfolios();
			$this->Log_NOTICE( "Sell stocks - Shares: " . $this->Getnumbershares() . " for $" . $this->Gettransactiondollars() );
			if( $this->Gettransactiondollars() > $this->Getbuybookvalue() )
			{
				$this->Setwinratio( $this->Getwinratio() + 1 );
				$this->Setwinsize( $this->Gettransactiondollars() - $this->Getbuybookvalue() + $this->Getwinsize() );
			}
			else
			{
				$this->Setloseratio( $this->Getloseratio() + 1 );
				$this->Setlosesize( $this->Getbuybookvalue() - $this->Gettransactiondollars() + $this->Getlosesize() );
			}

			$this->Setbuybookvalue( 0 );
		}
	}
	/*@bool@*/ function ActionSellStock()
	{
		$this->Calcsharecost();
		if( $this->Getsharecost() == 0 )
		{
			$this->Log( "Invalid share price for " . $this->Getsymbol() . " on " . $this->Gettransactiondate() . ".  Can't sell when price 0 (" . $this->Getsharecost() . ")" );
			return FALSE;
		}
		
		//get the number of shares in the portfolio
		if( $this->Getsymbol() != $this->transaction_c->Getstocksymbol() )
		{
			$this->transaction_c->Setstocksymbol( $this->Getsymbol() );
			$this->Log( "Resetting transaction stock symbol" );
		}
		$shares = $this->transaction_c->CalculateSharesAvailableDate();
		$this->Log( "ActionSellStock calculated shares # " . $shares . " for stock " . $this->transaction_c->Getstocksymbol() );
		$this->Setnumbershares( $shares );  //NEED TO REVISIT THIS FCN
		if( $this->Getnumbershares() > 0 )
		{
			$this->Settransactiondollars( $this->Getnumbershares() * $this->Getsharecost() );
			$this->SellStock();
		}
		return TRUE;
	}
	function RunStrategy()
	{
		//LOOP Find the next date for a given stock
		$this->Log_NOTICE( "RunStrategy Looping" );
		$this->Log_NOTICE( "RunStrategy Start and End dates: " . $this->Gettransactiondate() . ":" . $this->Getenddate() );

		while(
			 $this->stockprices_c->Getnexttradedate() != NULL 
			 AND strtotime( $this->Gettransactiondate() ) <= strtotime( $this->Getenddate() )
		     )
		{
			$this->Setlastaction( $this->Getaction() );
			$this->Setaction( "None" );
			//$this->Log( "Finding next trade date from " . $this->stockprices_c->Getdate() . " for symbol " . $this->stockprices_c->Getsymbol() );
			$this->Settransactiondate( $this->stockprices_c->Getnexttradedate() );
		//	$this->Log( "Date search query was " . $this->stockprices_c->querystring );
			//Run the strategies
		// How must you prepare if trading both long and short positions.
		// Current assumption is LONG positions only.
			$this->SellStrategy(); //Do sell first so that you have the benefit of the extra money
			if( $this->Getaction() == "sellstock" )
			{
				$this->ActionSellStock();
			}
			else
			{
				//If we have a sell signal, we shouldn't get a buy signal too for the same stock same day
				$this->BuyStrategy();
				if( $this->Getaction() == "buystock" )
				{
					if( $this->Liquidity() AND $this->Volatility() )
					{
						$this->moneymanagement();
						$this->ActionBuyStock();
					}
				}
			}
		}
		//$this->CalcBookMarketValues();
		//$this->Log_NOTICE( "Ending Market and Book values: " . $this->Getportfolio_marketvalue() . ":" . $this->Getportfolio_bookvalue() );
		$this->ActionSellStock();
	        $dollarsavailable = $this->transaction_c->CalculateDollarsAvailableDate();
		$this->Setendcash( $dollarsavailable );
		$ratios = ($this->Getwinratio() + $this->Getloseratio() );
		if ( 0 <> $ratios )
			$this->Setsuccessratio( $this->Getwinratio() / $ratios );
		else
			$this->Setsuccessratio( 0 );
		$this->CalcExpectancy();
		$this->Log_NOTICE( "Ending cash available after selling stocks: $" . $this->Getendcash() . " for a yield of " . $this->Getendcash() / $this->Getstartcash() . " with a success ratio of " . $this->Getsuccessratio() . " and an expectancy of $" . $this->Getexpectancy() . " for each trade" );
	}
	/***************************************************************
	*       @function moneymanagement
	*       @param
	*       @see
	*       @return 
	*
	*	Note: Risk and Money management rules should include:
	*	   1. defining your trading float       (Calcdollars2invest)
	*	   2. setting a maximum loss            (risksize)
	*	   3. setting you initial stops		(CalcInitialStops  (transaction_close table))
	*	   4. calculating your trade sizes.	(Buy/Sell Stock)
	*	NEVER TRADE MORE THAN x% OF YOUR PORTFOLIO IN ONE TRADE where x is customarily 10%.
	*	userpref_tlv "Max_Pct_Portfolio_single_trade"
	*	# What is the heat of your trading.
	*	# When do you experience expectation of success.				(rate of success)
	*	# When must you take a loss to avoid larger losses.				(stop size, candlesticks, trends)
	*	# If you are on a losing streak do you trade the same.				(reinvest strategies)
	*	# How must you prepare if trading both long and short positions.
	*	# Does a portfolio of long and short allow one to trade more positions.		(turtle 4 weight in a sector concept)
	*	# How is your trading adjusted with accumulated new profits.			(turtle risk management concept)
	*	# How is volatility handled.							(risk handling)
	*	# How do you prepare yourself psychologically.
	*	# Have you tested (risk handling)your bet sizing.
	*
	*	//Screen - investor sentiment
	*	//Trend - MACD, RSI, Support, Resistance
	*	//Optimal - Support and Resistance levels
	*	//Risk management - formulas to price exit points up and down
	*	//Momentum - in and out with gain, etc
	***************************************************************/
	function moneymanagement()
	{
		//Money and Risk management
		//require_once( '../strategies/moneymanagement.php' );
		$_SESSION['username'] = $this->Getuser();
		$_SESSION['transactiondate'] = $this->Gettransactiondate();
		$_SESSION['account'] = $this->Getaccount();
		$this->Calcdollars2invest();
		$this->risksize();
		$this->Log( "MoneyManagement Dollars avail: " . $this->Getdollars2invest() . " with risk size: " . $this->Getdollars2risk() );
		//Set initial stop sizes as appropriate for the strategy
		$this->CalcInitialStops(); //To be overridden by child classes
	}
	/***************************************************************
	*       @function Calcdollars2invest
	*       @param
	*       @see
	*       @return bool
	*
	*	defining your trading float       (dollars2invest)
	*	How is your trading adjusted with accumulated new profits.	(turtle risk management concept)
	*
	***************************************************************/
	/*@bool@*/ function Calcdollars2invest()
	{
	        /***************************************************************
	        *
	        *       Portfolio size
	        *               Need to know the portfolio size to determine
	        *               the maximum trade size
	        *                       marketvalue
	        *                       bookvalue
	        *                       cash available
	        *                       account
	        *               However the portfolio is an up to date table
	        *               so we need to calculate out of transactions
	        *               when not looking at today's values.
	        *
	        ***************************************************************/
	
		$this->CalcBookMarketValues();
	        //Risk a maximum of maxsingletrade% of the portfolio or dollarsavailable, which ever is less
	        //maxsingletrade
		$this->Calcfloat();	
		$this->Setdollars2invest( floor( $this->Getfloat() ) );
	        return TRUE;
	}
	function CalcBookMarketValues()
	{
		if( "" == $this->portfolio_c->Getaccount() ) 
	        	$this->portfolio_c->Setaccount( NULL );
		$this->portfolio_c->fieldspec['username']['extra_sql']="";
		$this->ClearPortfolioVAR();
		$this->portfolio_c->GetVARRow("sum(marketvalue) as portfolio_marketvalue, sum(bookvalue) as portfolio_bookvalue");
		$this->Setportfolio_marketvalue( $this->portfolio_c->resultarray[0]['portfolio_marketvalue'] );
		$this->Setportfolio_bookvalue( $this->portfolio_c->resultarray[0]['portfolio_bookvalue'] );
		return TRUE;
	}
	/***************************************************************
	*       @function Calcmaxsingletrade
	*       @param 
	*       @see
	*       @return 
	*
	*	Taking application and USER preference settings for
	*	the maximum percentage of the portfolio to trade (buy)
	*	on one trade
	*
	*       Find default values for the user in terms of risk
	*       tolerance, size, etc
	*
	*       In any one trade we should never BUY more than 10% of
	*	our total portfolio.
	*       In any one trade we should never RISK more than 1% of
	*       our total (all accounts) equity.  If we also consider
	*       asset allocation, this would also include house, car,
	*       pension plans, etc.
	*
	***************************************************************/
	function Calcmaxsingletrade()
	{
	        /***************************************************************
	        *
	        *
	        ***************************************************************/
	        $maxsingletrade = 0;
	        $maxsingletradepct = 0;
	
	        $pref = $this->userpref_c->RetrievePref( $this->Getuser(), "Max_Pct_Portfolio_single_trade" );
	        if( isset( $pref ))
	        {
	                $maxsingletradepct = $pref;
	        }
	        else
	 	{
	                $maxsingletradepct = MM_SingleTradeRisk;
	        }
	        $maxsingletrade = $maxsingletradepct / 100;
		$this->Setmaxsingletrade( $maxsingletrade );
		return;
	}
	/***************************************************************
	*       @function Calcmaxriskpct
	*       @param 
	*       @see
	*       @return float
	*
	*	Taking application and USER preference settings for
	*	the maximum risk percentage of the portfolio to risk
	*	on one trade
	*
	*       In any one trade we should never BUY more than 10% of
	*	our total portfolio.
	*       In any one trade we should never RISK more than 1% of
	*       our total (all accounts) equity.  If we also consider
	*       asset allocation, this would also include house, car,
	*       pension plans, etc.
	*
	***************************************************************/
	function Calcmaxriskpct()
	{
	        $pref = $this->userpref_c->RetrievePref( $this->Getuser(), "Money_Management_Maxrisk_pct" );
	        if( isset( $pref ))
	        {
	                $maxriskpct = $pref;
	        }
	        else
	        {
	                $maxriskpct = MM_Maxrisk;
	        }
	        $maxrisk = $maxriskpct / 100;
		$this->Setmaxrisk( $maxrisk );
		return $maxrisk;
	}
		
	/***************************************************************
	*       @function risksize
	*       @param 
	*       @see
	*       @return float dollar amount to risk
	*
	*	setting a maximum loss            (risksize)
	***************************************************************/
	function risksize()
	{
		$dollars2risk = $this->Getdollars2invest();
		$maxrisk = $this->Calcmaxriskpct();
	
	        if( isset( $this->portfolio_marketvalue ))
	                $market2risk = $this->Getportfolio_marketvalue() + $this->Getcash();
	        else
	                $market2risk = $dollars2risk;		//This should be the case of where we own NO stocks
	        if( isset( $this->portfolio_bookvalue ))
	                $book2risk = $this->Getportfolio_bookvalue() + $this->Getcash();
	        else
	                $book2risk = $dollars2risk;  		//This should be the case of where we own NO stocks
		
		$this->Log( "Dollars, Book, Market, MaxRisk: " . $dollars2risk . ":" . $market2risk . ":" . $book2risk . ":" . $maxrisk );
		$this->Setdollars2risk( floor( min( $dollars2risk, min( $book2risk, $market2risk ) * $this->Getmaxrisk() ) ) );
	        return TRUE;
	}
	/***************************************************************
	*       @function ClearStockpricesVAR
	*       @param 
	*       @see
	*       @return bool
	*
	*	Clear the values from columns that we don't want to select
	*	upon with a GetVARRow 
	***************************************************************/
	function ClearStockpricesVAR()
	{
		 $this->stockprices_c->adjustedclose = NULL;
		 $this->stockprices_c->volume = NULL;
		 $this->stockprices_c->day_close = NULL;
		 $this->stockprices_c->day_open = NULL;
		 $this->stockprices_c->day_high = NULL;
		 $this->stockprices_c->day_low = NULL;
		return TRUE;
	}
	/***************************************************************
	*       @function ClearPortfolioVAR
	*       @param 
	*       @see
	*       @return bool
	*
	*	Clear the values from columns that we don't want to select
	*	upon with a GetVARRow 
	***************************************************************/
	function ClearPortfolioVAR()
	{
		$this->portfolio_c->numbershares = NULL;
		$this->portfolio_c->bookvalue = NULL;
		$this->portfolio_c->marketvalue = NULL;
		$this->portfolio_c->profitloss = NULL;
		$this->portfolio_c->marketbook = NULL;
		$this->portfolio_c->yeild = NULL;
         	$this->portfolio_c->dividendbookvalue = NULL;
         	$this->portfolio_c->currentprice = NULL;
         	$this->portfolio_c->annualdividendpershare = NULL;
         	$this->portfolio_c->annualdividend = NULL;
         	$this->portfolio_c->dividendpercentbookvalue = NULL;
         	$this->portfolio_c->dividendpercentmarketvalue = NULL;
         	$this->portfolio_c->dividendyield = NULL;
         	$this->portfolio_c->percenttotalmarketvalue = NULL;
         	$this->portfolio_c->percenttotalbookvalue = NULL;
         	$this->portfolio_c->percenttotaldividend = NULL;
         	$this->portfolio_c->lastupdate = NULL;

		return TRUE;
	}
	/***************************************************************
	*       @function CalcInitialStops 
	*       @param 
	*       @see
	*       @return bool
	*
	*	To be over ridden by child classes
	*	Capital preservation v. capital appreciation.
	*	When must you take a loss to avoid larger losses. (stop size, candlesticks, trends)
	*
	*	Different ways to size the initial stop:
	*		MaxRisk per trade against the cost of the share ie 1% of the price.  However
	*			this will stop out very often as a 1% move isn't unusual
	*		A factor times the ATR.  If we choose 2 days worth then we shouldn't stop
	*			out for at least 2 days and if we have any gains, more.  ATR = MAX( High0-Low0, High0-Close1, Close1 - Low0 )
	*		Other trend indicators
	*
	***************************************************************/
	function CalcInitialStops()
	{
		$this->Setinitialstopsize( $this->Getsharecost() * $this->Getmaxrisk() );
		return FALSE; //To be overridden by child classes
	}
	/***************************************************************
	*       @function ReinvestmentStrategy
	*       @param 
	*       @see
	*       @return bool
	*
	*	To be over ridden by child classes
	*	If you are on a losing streak do you trade the same.	
	*
	***************************************************************/
	function ReinvestmentStrategy()
	{
		return TRUE;  // If you are on a losing streak do you trade the same.
	}
	/***************************************************************
	*       @function Calcfloat
	*       @param 
	*       @see
	*       @return 
	*
	*	To be over ridden by child classes
	*	The float is how much you can spend in 1 transaction
	*
	***************************************************************/
	function Calcfloat()
	{
	        $dollarsavailable = 0;
	        $dollarsavailable = $this->transaction_c->CalculateDollarsAvailableDate();
		$this->Setcash( $dollarsavailable );
	        $this->Log( "Dollars available " . $dollarsavailable );

		//How is your trading adjusted with accumulated new profits.	(turtle risk management concept)
		//Currently using the min of dollars cash, marketvalue or bookvalue
		//Could also use adjusted float based upon market/book ratio
		$book = $this->Getportfolio_bookvalue();
		$market = $this->Getportfolio_marketvalue();
		$maxpct = $this->Getmaxsingletrade();
		$this->Log( "Dollars-cash, Book, Market, MaxPortfolioPct: " . $dollarsavailable . ":" . $book . ":" . $market . ":" . $maxpct );
	        $dollars2invest = min( $dollarsavailable, min( $book + $dollarsavailable, $market + $dollarsavailable ) * $maxpct );
		$this->Setfloat( $dollars2invest );
	}
	/***************************************************************
	*       @function Volatility
	*       @param 
	*       @see
	*       @return bool
	*
	*	To be over ridden by child classes
	*	Volatility is simply a measurement of how much a security moves. Not whether it goes up or down, just how much it fluctuates.
	*	It is important to trade securities that move enough for you to make a profit. Of course you don't 
	*	want securities that are so volatile you canâget to sleep at night.  On the other hand, you don't want something that moves at 
	*	such a snail's pace that it is not delivering the returns you are after. One way to identify volatility is using the ATR method,
	*	which indicates how much a security will move, on average, over a certain period.
	*
	***************************************************************/
	function Volatility()
	{
		return TRUE; //Default until the fcn is developed
		return FALSE;
	}
	/***************************************************************
	*       @function Liquidity
	*       @param 
	*       @see
	*       @return bool
	*
	*	To be over ridden by child classes
	*	Liquidity is an important determinant because you want to be trading securities that you can buy and sell quickly.
	*	You never want to be caught in a position where you want out but thereâno one to buy.
	*	Depending on the size of your float, you might want the average daily trade volume to be greater than $400,000 (ave vol * closing price).
	*
	***************************************************************/
	function Liquidity()
	{
		return TRUE; //Default until the fcn is developed
		return FALSE;
	}
	/***************************************************************
	*       @function CalcExpectancy
	*       @param 
	*       @see
	*       @return bool 
	*
	*	To be over ridden by child classes
	*	Percentage of Wins * average win size - percentage of losses * average loss size
	*	You need this to be a positive expectancy or this strategy will definately lose you money
	*
	***************************************************************/
	function CalcExpectancy()
	{
		if ( 0 <> $this->Getwinratio() )
			$win = $this->Getsuccessratio() * ( $this->Getwinsize() / $this->Getwinratio() );
		else
			$win = 0;
		if( 0 < $this->Getloseratio() )
			$loss = (1 - $this->Getsuccessratio()) * ( $this->Getlosesize() / $this->Getloseratio() );
		else
			$loss = 0;
		$this->Setexpectancy( $win - $loss );
		return TRUE; //Default until the fcn is developed
	}
	function AddUser( $surname = "BacktestSurname", $firstname = "BacktestFirstname", $emailaddress = "fraser.ks@gmail.com", $password = "", $roles_id = "00000000004" )
	{
		$username = $this->Getuser();
	        if( require_once( 'security/users.class.php' ))
	        {
	                $insert['username'] = $username;
	                $insert['surname'] = $surname;
	                $insert['firstname'] = $firstname;
	                $insert['emailaddress'] = $emailaddress;
	                $insert['password'] = $password;
	                $insert['roles_id'] = $roles_id;
	
	                $users = new users();
	                $users->where = "username = '$username'";
	                $users->Select();
	                if( isset( $users->resultarray[0]['username'] ) AND $users->resultarray[0]['username'] == $username )
	                {
	                        $this->Log_INFO( "Updating user $username" );
	                        $users->Update( $insert );
	                }
	                else
	                {
	                        $this->Log_INFO( "Adding user $username" );
	                        $users->Insert( $insert );
	                }
			$this->transaction_c->deleteusertransactions($this->Getuser()); //Assumption we run the same test multiple times...
			$this->portfolio_c->deleteuserdata($this->Getuser()); //Assumption we run the same test multiple times...
 			$this->transaction_c->useraccountaddcash($this->flog, $this->Getuser(), $this->Getcash(), $this->Gettransactiondate(), $this->Getcurrency(), $this->Getaccount());
			$this->Log( "Created user" . $firstname . " " . $surname );
	                return SUCCESS;
	        }
		$this->Log_EMERG( "Can't create user" );
	        exit( FAILURE );
	}
	/***************************************************************
	*       @function Calcsymbolheat
	*       @param 
	*       @see
	*       @return bool 
	*
	*	To be over ridden by child classes
	*
	* 	In portfolio management, we call the distributed bet size the heat of the portfolio. 
	*	A diversified portfolio risking 2% on each of five instrument & has a total heat 
	*	of 10%, as does a portfolio risking 5% on each of two instruments.
	*
	*	Studies show that trading systems have an inherent optimal heat.  The heat level
	*	is more important than trade timing.  Most traders are unaware of this.
	*
	***************************************************************/
	function Calcsymbolheat()
	{
	}
}

?>



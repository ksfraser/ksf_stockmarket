<?php

/***************************************************************
*
*	Calculate the scores that Buffet uses to evaluate stocks
*
*	Depends on
*		Having recent up to date BOND rates in table bondrate
*		Up to date currentprice in stockinfo
*		Up to date outstanding shares in fin_statement
*		Up to date incomegrowth in fin_statement
*		Up to date ownersearnings in fin_statement
*		fin_statment was updated in the last 35 days.
*
****************************************************************/

/*****************************************************************
*
*	Definitions
*
*      //debtratio     totaldebt/totalassets
*                //acceptabledebt netincome/revenue
*                //roe  net_income/shareholder_equity - 15-20% is attractive investment
*                //lowcost operating margin > 10%
*
*                //ROA - net income / total assets - how well managemtn is using the company resources.
*                //ROCE (return on captial employed) = Net income/(Debt + shareholder equity)
*                //Profit Margins
*                //      Gross Profit Margin = Gross profit/Net Sales (revenue)
*                //      Operating = Operating profit/Net Sales
*                //              As the management controls the operating expenses, this value tells how well management is doing
*                //      Pretax = pretax profit/net sales
*                //      Net = Net Income/Net Sales
*		//marketcap = outstandingshares * currentprice
*		//update evalmarket e, stockinfo s set marketcap = outstandingshares * currentprice where e.idstockinfo = s.idstockinfo;
*		//ownerearnings =  netincome + depreciation + depletion + amortization - capitalexpenses - workingcapital
*		//update evalmarket set ownerearnings =  netincome + depreciation + depletion + amortization - capitalexpenses - workingcapital
*		//marginsafety = 100 * $ownerearnings - marketcap / marketcap
*		//update evalmarket e, fin_statement f set marginsafety = ((totalasset - totalliability) / marketcap) - 1 where e.idstockinfo = f.idstockinfo
*		//Growthrate and discountrate
*
**********************************************************************/




require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

//20090412 KF fin_statement has most of these values off of the google financial statements

require_once( '../../model/evalmarket.class.php' );
require_once( '../../model/evalfinancial.class.php' );
require_once( '../../model/fin_statement.class.php' );
require_once( '../../model/bondrate.class.php' );
require_once( '../../model/investorplace.class.php' );

$investorplace = new investorplace();
$market = new evalmarket();

/*****************************************
*
*	Get the next 10 years bond rates
*	to be used to calculate the risk
*	free return rate so that the future
*	value of the company can be calculated
*
****************************************/
$bond = new bondrate();
$bond->where = "calendaryear > now()";
$bond->orderby = "calendaryear";
$bond->limit = "10";
$bond->Select();
/*****************************************
*	End BOND RATE SELECT
*****************************************/

$finstatement = new fin_statement();
$finance = new evalfinancial(); //Can update values in evalfinance from fin_statement


//value, marketcap, marginsafety, netvalue


//marketcap = outstandingshares * currentprice
//update evalmarket e, stockinfo s set marketcap = outstandingshares * currentprice where e.idstockinfo = s.idstockinfo;

//marginsafety = 100 * $ownerearnings - marketcap / marketcap
//update evalmarket e, fin_statement f set marginsafety = ((totalasset - totalliability) / marketcap) - 1 where e.idstockinfo = f.idstockinfo

//Growthrate and discountrate
$finstatement->querystring = '
SELECT 	distinct(f.idstockinfo) as idstockinfo, 
	f.outstandingshares * s.currentprice as marketcap, 
	f.outstandingshares as outstandingshares, 
	f.incomegrowth as incomegrowth,
	f.ownerearnings as ownerearnings,
	s.currentprice / f.earningpershare as pe
FROM 	stockinfo s, 
	fin_statement f 
WHERE s.idstockinfo = f.idstockinfo
	and f.lasteval > DATE_SUB(now(), INTERVAL 35 day)
ORDER BY f.lasteval desc';

$finstatement->GenericQuery();

$discountrate = 10;

foreach( $finstatement->resultarray as $update )
{
//	var_dump( $update );
	//$update['value'] = 100 * 1000000 * $update['ownerearnings'] / ( $discountrate - $update['incomegrowth'] );
	//Future Value is the total owners earnings discounted to today's value
	//by the long term bond rate + a margin of safety (3%)
	//Will look 10 years out on our investments
	$ownerearnings = 1000000 * $update['ownerearnings'];
	$cashflow = $ownerearnings;
	$growth = $update['incomegrowth'];
	$discountfactor = 1;
	$futurevalue = 0;
//	echo "ownerearnings = 1000000 * update['ownerearnings']: $ownerearnings\n";
//	echo "cashflow = ownerearnings: $cashflow\n";
//	echo "growth = update['incomegrowth']: $growth\n";
//	echo "discountfactor = 1: $discountfactor\n";
//	echo "futurevalue = 0: $futurevalue\n";
	foreach( $bond->resultarray as $bvalue )
	{
	//Split growth values
		$cashflow += $cashflow * $growth;
		$discount = $bvalue['bondrate'] + 3;
		if( $discount < 10 )
			$discount = 10;
		$discountfactor = $discountfactor / ( 1 + $discount/100 );
		$discounted = $cashflow * $discountfactor;
		$futurevalue += $discounted;
	//Constant growth values
/*
		$cashflow = $cashflow * ( 1 + ($growth - $bvalue['bondrate']) / 100 );
		$futurevalue += $cashflow;
*/
	}
//	echo "Post eval: \n";
//	echo "Cashflow: $cashflow\n";
//	echo "Discount: $discount\n";
//	echo "Discounted: $discounted\n";
//	echo "Future Value: $futurevalue\n";
//	echo "Discount Rate: " . $discountrate . "\n";
//	echo "Growth Rate: " . $update['incomegrowth'] . "\n";
	if ($discountrate - $update['incomegrowth'] <> 0)
	{
		$update['value'] = $futurevalue + $discounted / ( $discountrate - $update['incomegrowth'] ) ;
	}
	else
	{
		$update['value'] = -1;
	}


	if ( $update['marketcap'] <> 0 )
	{
		$update['marginsafety'] = 100 * $ownerearnings / $update['marketcap'];
	}
	else
	{
		$update['marginsafety'] = 0;
	}
	//var_dump( $update );
	//sleep( 5 );
	$market->Insert( $update );
	$finance->Insert( $update );
	$investorplace->Insert( $update );
	
}


?>

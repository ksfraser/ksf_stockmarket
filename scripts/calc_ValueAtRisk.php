<?php

echo __FILE__;
require_once( 'library.statistics.php' );
require_once("Math/Stats.php");

require_once( $MODELDIR . '/include_all.php' );
require_once( $MODELDIR . '/stockprices.class.php' );
require_once( $MODELDIR . '/portfolio.class.php' );
$stockprices = new stockprices();
$stats = new Math_Stats();
$portfolio = new portfolio();


// my $crit = 2.326348;          # 1% critical value of the Normal distribution
// my $crit = 1.644584;         # 5% critical value of the Normal distribution

/*20090707 KF
* Calculate the value at risk for a portfolio
*/

$portfolio->select = "stocksymbol, marketvalue";
$portfolio->where = "username = 'kevin'";
$portfolio->orderby = "stocksymbol";
$portfolio->Select();
foreach( $portfolio->resultarray as $row )
{

	//Select the stocks from the user's portfolio
	//Get the daily close value for the stock
	//Calculate returns
		//(Todays price/yesterday's price) - 1
		//Add these sums together
		//Get the standard deviation, MIN and MAX
	$stockprices->querystring = "select day_close from stockprices where symbol = '" . $row['stocksymbol'] . "'";
	$symbollist[] = $row['stocksymbol'];
	$stockprices->GenericQuery();
	foreach( $stockprices->resultarray as $row )
	{
		$dataarray[] = $row['day_close'];
	}
	$stats->setData( $dataarray );
	
	$res = $stats->calcFull();
	echo "Calculated: Mean " . $res['mean'] . " and StdDev " . $res['stdev'] . "\n";
	$volatility['stocksymbol'] = $res['stdev'];
	$quintile['stocksymbol'] = $stats->percentile(1);
	$quintile['stocksymbol'] = $res['percentile'];
	$marketvalue['stocksymbol'] = $row['marketvalue'];
}

foreach( $symbollist as $stocka )
{
	foreach( $symbollist as $stockb )
	{
		if( $stocka < $stockb )
		{
			$stockprices->querystring = " SELECT a.day_close, b.day_close
			FROM stockprices a, stockprices b
			WHERE a.symbol = " . $stocka . "
			AND b.symbol = " . $stockb . "
			AND a.date <= " . date( 'Y-m-d' ) . "
			AND a.date >= " . date( 'Y-m-d', mktime(0, 0, 0, date("m")  , date("d")-1, date("Y")) ) . "
			AND a.date = b.date
			AND a.day_close !=0
			AND b.day_close !=0
			ORDER BY a.date";
			$stockprices->GenericQuery();

			 $correlation[$stocka][$stockb] = least_squares_fit( $stockprices->resultarray );
		}
		else
		if( $stocka > $stockb )
		{
			$correlation[$stocka][$stockb] = $correlation[$stockb][$stocka];
		}
		else
		{
			//It is the same symbol compared against itself so a perfect correlation
		 	$correlation[$stocka][$stockb] = 1;
		}
	}
}
//Aggregate Risk
/*
	 # aggregate risk:
	  # VaR is z_crit * sqrt(horizon) * sqrt (X.transpose * Sigma * X)
	  # where X is position value vector and Sigma the covariance matrix
	  # given that Perl is not exactly a language for matrix calculus (as
	  # eg GNU Octave), we flatten the computation into a double loop
*/
$sum = 0;
foreach ( $pos as $pkey ) 
{
	//pos is an array of the marketvalue per share
	//vol is the stddeviation per share
	//cor is the correlation between the 2 shares
	if ( defined($pos[$pkey]) && defined($vol[$pkey]) ) 
	{
		foreach ( $vol as $vkey ) 
		{
	        	if ( 	defined($pos[$vkey]) 
				&& defined($vol[$vkey]) 
				&& defined($cor[$vkey][$pkey]) 
		   	   ) 
			{
	          		$sum += $pos[$pkey] * $pos[$vkey] 
				* $vol[$vkey] * $vol[$pkey] * $cor[$vkey][$pkey];
	        	}
      		}
	}
}
$valueatrisk = $crit * sqrt($sum);

//Marginal Value At Risk
/*
 ## marginal var
  my %margvar;
  foreach my $outer (keys %pos) {
    my $saved = $pos{$outer};
    my $sum = 0;
    $pos{$outer} = 0;
    foreach my $pkey (keys %pos) {
      if (defined($pos{$pkey}) && defined($vol{$pkey})) {
        foreach my $vkey (keys %vol) {
          if (defined($pos{$vkey}) && defined($vol{$vkey}) &&
              defined($cor{$vkey}{$pkey})) {
            $sum += $pos{$pkey} * $pos{$vkey} * $vol{$vkey} * $vol{$pkey}
                    * $cor{$vkey}{$pkey};
          }
        }
      }
    }
    $margvar{$outer} = $crit * sqrt($sum) - $var;
    $pos{$outer} = $saved;
*/


?>

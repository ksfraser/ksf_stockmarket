<?php

//Remove duplicate symbols from stockinfo

require_once( 'include_all.php' );
//echo "required include_all.php\n";
require_once( $MODELDIR . '/stockinfo.class.php' );
//echo "required stockinfo.class.php\n";

$si = new stockinfo();

$si->select = "distinct stocksymbol";
$si->Select();
foreach( $si->resultarray as $row )
{
	$symbol = new stockinfo();
	$symbol->select = "idstockinfo";
	$symbol->where = "stocksymbol = '" . $row['stocksymbol'] . "'";
	//var_dump( $row['stocksymbol'] );
	$symbol->Select();
	//delete the duplicates above the first 1
	$count = count( $symbol->resultarray );
	//var_dump( $count );
	$rep = new stockinfo();
	if( $count > 1 )
	{
		//Need to ensure the value isn't used anywhere else first
		$canonical = $symbol->resultarray[0]['idstockinfo']; //This is the good value
		for( $count--; $count > 0; $count-- )
		{
			/* The following classes all have idstockinfo in them
			*/
			$classes = array(
			'evalbusiness',
			'evalfinancial',
			'evalmanagement',
			'evalmarket',
			'evalsummary',
			'evalvalue',
			'fin_statement',
			'hedgefolios',
			'investorplace',
			'iplace_calc',
			'quarter_statement',
			'ratios',
			'stockalert',
			'stockinfo',
			'transaction',
			'transaction_close',
			);
			foreach ( $classes as $class )
			{
				$rep->querystring="update " . $class . " set idstockinfo='" . $canonical . "' where idstockinfo ='" . $symbol->resultarray[$count]['idstockinfo'] . "'";
				$rep->GenericQuery();
			//	var_dump( $rep->querystring );
			}
			$rep->querystring="delete from stockinfo where idstockinfo='" . $symbol->resultarray[$count]['idstockinfo'] . "'";
			//var_dump( $rep->querystring );
			$rep->GenericQuery();
		}
	}
}



?>

<?php


function getfuturevalue( $data, $bond )
{
	if( isset( $data['discountrate'] ))
		$discountrate = $data['discountrate'];
	else
		$discountrate = 10;

	//Future Value is the total owners earnings discounted to today's value
	//by the long term bond rate + a margin of safety (3%)
	//Will look 10 years out on our investments
	$ownerearnings = 1000000 * $data['ownerearnings'];
	$cashflow = $ownerearnings;
	$growth = $data['averagegrowthrate'];
	$discountfactor = 1;
	$futurevalue = 0;
	foreach( $bond as $bvalue )
	{
	//Split growth values
		$cashflow += $cashflow * $growth;
		$discount = $bvalue['bondrate'] + 3;
		$discountfactor = $discountfactor / ( 1 + $discount/100 );
		$discounted = $cashflow * $discountfactor;
		$futurevalue += $discounted;
	//Constant growth values
/*
		$cashflow = $cashflow * ( 1 + ($growth - $bvalue['bondrate']) / 100 );
		$futurevalue += $cashflow;
*/
	}
	if ( ($discountrate - $data['percentgrowth'][1]) <> 0)
	{
		$update['value'] = $futurevalue + $discounted / ( $discountrate - $data['percentgrowth'][1] ) ;
	}
	else
	{
		$update['value'] = -1;
	}

	if ( $data['marketcap'] <> 0 )
	{
		$update['marginsafety'] = 100 * $ownerearnings / $data['marketcap'];
	}
	else
	{
		$update['marginsafety'] = 0;
	}
	return $update;
}


?>

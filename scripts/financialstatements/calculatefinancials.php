<?php

require_once( '../fundamentalanalysis/earningsaccel.php' );
require_once( '../fundamentalanalysis/earningsgrowth.php' );
require_once( '../fundamentalanalysis/dividendincreases.php' );
require_once( '../fundamentalanalysis/shareholderprofitgoal.php' );

function calculatefinancials( $input )
{
$update = array();
/*
	$fp = fopen( "calculatefinancials." . date( 'Ymdhms' ) . ".input", "w" );
	fwrite( $fp, print_r( $input, true ) );
	fclose( $fp );
*/
//Copy variables that aren't touched in here to be passed back
//Only concerned with this year
	foreach( $input as $key=>$value )
	{
		//$update['outstandingshares'] = $input['outstandingshares'][0];
		//If a value is shown as '-' then it is 0 or nil
		if( $value[0] <> "-" )
			$update[$key] = $value[0];
		else
			$update[$key] = 0;
	}
	//Also need EPS and DPS historical
	if( isset( $input['earningpershare'] ))
	{
		$update['earningspershare1'] = $input['earningpershare'][1];
		$update['earningspershare2'] = $input['earningpershare'][2];
		$update['earningspershare3'] = $input['earningpershare'][3];
		if( $update['earningspershare1'] == '-' )
			$update['earningspershare1'] = 0;
		if( $update['earningspershare2'] == '-' )
			$update['earningspershare2'] = 0;
		if( $update['earningspershare3'] == '-' )
			$update['earningspershare3'] = 0;
	}
	if( isset( $input['dividendpershare'] ))
	{
		$update['dividendpershare1'] = $input['dividendpershare'][1];
		$update['dividendpershare2'] = $input['dividendpershare'][2];
		$update['dividendpershare3'] = $input['dividendpershare'][3];
		if( $update['dividendpershare1'] == '-' )
			$update['dividendpershare1'] = 0;
		if( $update['dividendpershare2'] == '-' )
			$update['dividendpershare2'] = 0;
		if( $update['dividendpershare3'] == '-' )
			$update['dividendpershare3'] = 0;
	}
	//var_dump( $update );
		
	//Growth
	if( isset( $input['netincome'] ))
	{
		if( (float)$input['netincome'][1] <> 0 )
		{
			$percentgrowth1 = ( 100 * ( (float)$input['netincome'] - (float)$input['netincome'][1]) )
						/ (float)$input['netincome'][1];
			if( $percentgrowth1 <= 1 )
				$percentgrowth1 = 0;
			$input['percentgrowth'][1] = $percentgrowth1;
			$update['percentgrowth'][1] = $percentgrowth1;
		}
		else
			$update['percentgrowth'][1] = 0;
		if( (float)$input['netincome'][2] <> 0 )
		{
			$percentgrowth2 = ( 100 * ( (float)$input['netincome'][1] - (float)$input['netincome'][2]) )
						/ (float)$input['netincome'][2];
			if( $percentgrowth2 <= 1 )
				$percentgrowth2 = 0;
			$input['percentgrowth'][2] = $percentgrowth2;
			$update['percentgrowth'][2] = $percentgrowth2;
	
		}
		else
			$update['percentgrowth'][2] = 0;
		if( (float)$input['netincome'][3] <> 0 )
		{
			$percentgrowth3 = ( 100 * ( (float)$input['netincome'][2] - (float)$input['netincome'][3]) )
						/ (float)$input['netincome'][3];
			if( $percentgrowth3 <= 1 )
				$percentgrowth3 = 0;
			$input['percentgrowth'][3] = $percentgrowth3;
			$update['percentgrowth'][3] = $percentgrowth3;
		}
		else
			$update['percentgrowth'][3] = 0;
		$percentgrowthsum = 0;
		$percentgrowthcount = 0;
		if( isset( $percentgrowth1 ))
		{
			$percentgrowthsum += $percentgrowth1;
			$percentgrowthcount++;
		}
		if( isset( $percentgrowth2 ))
		{
			$percentgrowthsum += $percentgrowth2;
			$percentgrowthcount++;
		}
		if( isset( $percentgrowth3 ))
		{
			$percentgrowthsum += $percentgrowth3;
			$percentgrowthcount++;
		}
		if( $percentgrowthcount++ > 0 )
			$averagegrowth = $percentgrowthsum / $percentgrowthcount;
		else
			$averagegrowth = 0;
		$update['averagegrowthrate'] = $averagegrowth;
		$update['incomegrowth'] = $averagegrowth;

		$update['revenuegrowth']  = (float)$input['netincome'][0] - (float)$input['netincome'][1];
		$update['revenuegrowth2'] = (float)$input['netincome'][0] - (float)$input['netincome'][2];
		$update['revenuegrowth3'] = (float)$input['netincome'][0] - (float)$input['netincome'][3];
	}
	else
	{
		$input['netincome'][0] = 0;
		$update['netincome'] = 0;
		$update['percentgrowth'][0] = 0;
		$update['percentgrowth'][1] = 0;
		$update['percentgrowth'][2] = 0;
		$update['percentgrowth'][3] = 0;
		$update['averagegrowthrate'] = 0;
		$update['incomegrowth'] = 0;
		$update['revenuegrowth'] = 0;
		$update['revenuegrowth2'] = 0;
		$update['revenuegrowth3'] = 0;
	}
	if( !isset( $input['netincome'][0] ))
		$input['netincome'][0] = 0;
	if( !isset( $input['amortization'][0] ))
		$input['amortization'][0] = 0;
	if( !isset( $input['capitalexpenses'][0] ))
		$input['capitalexpenses'][0] = 0;
	if( !isset( $input['workingcapital'][0] ))
		$input['workingcapital'][0] = 0;
	if( !isset( $input['depletion'][0] ))
		$input['depletion'][0] = 0;
	if( !isset( $input['shares'][0] ))
		$input['shares'][0] = 0;
	if( !isset( $input['totalliability'][0] ))
		$input['totalliability'][0] = 0;
	if( !isset( $input['totalasset'][0] ))
		$input['totalasset'][0] = 0;
//Owner Earnings = Net Income + amortization + depreciation - Capital Expenses - Working Expenses + depletion
	$update['ownerearnings'] = (float)$input['netincome'][0] + (float)$input['amortization'][0] - (float)$input['capitalexpenses'][0] - (float)$input['workingcapital'][0] + $input['depletion'][0];
	$update['earningsaccel'] = getEarningsAccel( $update );
	$update['earningsgrowth'] = getEarningsGrowth( $update );
	//$update['depreciation'] = (float)$input['depreciation'][0];
	$update['depletion'] = (float)$input['depletion'][0];
	$update['amortization'] = (float)$input['amortization'][0];
	//$update['workingcapital'] = $update['workingcapital'][0];
	$update['capitalexpenses'] = (float)$input['capitalexpenses'][0];
	$update['outstandingshares'] = (float)$input['shares'][0] * 1000000;
//Annual Balance Sheet - Assets and Liabilities
	$update['netvalue'] = $input['totalasset'][0] - $input['totalliability'][0];
	$update['dividendincreases'] = getDividendIncreases( $input );
	$update['shareholderprofitgoal'] = getShareholderProfitGoal( $input );

	return $update;
}	

?>

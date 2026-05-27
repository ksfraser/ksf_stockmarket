<?php

//20090811 KF
//Calculating Correlation

//Defining Correlation as the relationship of 2 items having changes in the same direction
//IE One stock goes up, and another also goes up.
echo __FILE__;

function correlatedirection( $datearray, $changearrayA, $changearrayB )
{
	//$datearray is the list of events to check changes for.
	//For stocks would be dates, but for other items
	//would be a timeseries

	$sum = 0;
	$count = 0;
	foreach( $datearray as $date )
	{
		if( isset( $changearrayA[$date] ) )
		{
			if( isset( $changearrayB[$date] ))
			{
				if( $changearrayA[$date] > 0 and $changearrayB[$date] > 0 )
				{
					$correlation[$date] = 1;
					$sum++;
					$count++;
				}
				else if( $changearrayA[$date] < 0 and $changearrayB[$date] < 0 )
				{
					$correlation[$date] = 1;
					$sum++;
					$count++;
				}
				else
				{
					$correlation[$date] = 0;
					$count++;
				}
			}
			else
			{
				$correlation[$date] = 0;
				$count++;
			}
		}
		else
		{
			$correlation[$date] = 0;
			$count++;
		}
	}
	$correlation['sum'] = $sum;
	$correlation['count'] = $count;
	return $correlation;
}

function correlatemagnitudedirection( $datearray, $changearrayA, $changearrayB )
{
	//$datearray is the list of events to check changes for.
	//For stocks would be dates, but for other items
	//would be a timeseries

	$sumA = 0;
	$abssumA = 0;
	$countA = 0;
	$sumB = 0;
	$abssumB = 0;
	$countB = 0;

	foreach( $changearrayA as $value )
	{
		$sumA += $value;
		$abssumA += ABS( $value );
		$countA++;
	}
	foreach( $changearrayB as $value )
	{
		$sumB += $value;
		$abssumB += ABS( $value );
		$countB++;
	}
	$mediumA = $sumA / $countA;
	$mediumB = $sumB / $countB;
	$averageA = $abssumA / $countA;
	$averageB = $abssumB / $countB;

	$sum = 0;
	$count = 0;
	foreach( $datearray as $date )
	{
		if( isset( $changearrayA[$date] ) )
		{
			if( isset( $changearrayB[$date] ))
			{
				if( $changearrayA[$date] > 0 and $changearrayB[$date] > 0 )
				{
					$correlation[$date] = 1;
					$sum++;
					$count++;
				}
				else if( $changearrayA[$date] < 0 and $changearrayB[$date] < 0 )
				{
					$correlation[$date] = 1;
					$sum++;
					$count++;
				}
				else
				{
					$correlation[$date] = 0;
					$count++;
				}
			}
			else
			{
				$correlation[$date] = 0;
				$count++;
			}
		}
		else
		{
			$correlation[$date] = 0;
			$count++;
		}
	}
	$correlation['sum'] = $sum;
	$correlation['count'] = $count;
	return $correlation;
}

//TEST
$A[1] = 1;
$A[2] = 2;
$A[3] = 3;
$A[4] = 4;
$A[5] = 5;
$B[1] = 1;
$B[2] = 2;
$B[3] = 3;
$B[4] = -4;
$B[5] = -5;
$dates = array ( 1, 2, 3, 4, 5 );

$direction = correlatedirection( $dates, $A, $B );
var_dump( $direction );
echo "Direction Correlation = " . 
	$direction['sum'] . " on " .
	$direction['count'] . " datapoints for a " . 
	$direction['sum']/$direction['count'] . " correlation\n";

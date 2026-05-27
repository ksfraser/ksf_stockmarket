<?php

/**********************************************************************
*
*	20110807 KF Startmonth is now 1-12 rather than 0-11
*		extracted date checking code
*
************************************************************************/


function monthmaxday( $MONTH='1', $DAY='01' )
{
	if( $DAY < 1 )
		$DAY = 1;
	if( 
		$MONTH == 1
		|| $MONTH == 3
		|| $MONTH == 5
		|| $MONTH == 7
		|| $MONTH == 8
		|| $MONTH == 10
		|| $MONTH == 12
	  )
	{
		//These months have 31 days
		if( $DAY > 31 )
			$DAY = 31;
	}
	else
	if( 
		$MONTH == 4
		|| $MONTH == 6
		|| $MONTH == 9
		|| $MONTH == 11
	  )
	{
		//These months have 30 days
		if( $DAY > 30 )
			$DAY = 30;
	}
	else
	if( 
		$MONTH == 2
	  )
	{
		//These months have 28 days
		if( $DAY > 28 )
			$DAY = 28;
	}
	return $DAY;
}
?>

<?php

//Is the growth of the company earnings accellerating?

function getDividendIncreases( $data )
{
	if( !isset( $data['dividendpershare' ] ) )
	{
		return -1;
	}
	if( 	
 		   $data['dividendpershare' ][0] < $data['dividendpershare'][1]
 		OR $data['dividendpershare' ][1] < $data['dividendpershare'][2]
	  )
	{
		//Dividend has gone down in the last 3 years
		return 0;
	}
	else
	if( 	
 		( $data['dividendpershare' ][0] > $data['dividendpershare'][1]
 		  AND $data['dividendpershare' ][1] >= $data['dividendpershare'][2]
		)
		OR
 		( $data['dividendpershare' ][0] >= $data['dividendpershare'][1]
 		  AND $data['dividendpershare' ][1] > $data['dividendpershare'][2]
		)
	  )
	{
		//Dividend increased at least one year
		//And didn't go down
		return 1;
	}
	else
	{
		//Dividend the same all 3 years
		return 0;
	}
}

?>

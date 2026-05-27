<?php

//Is the growth of the company earnings accellerating?

function getShareholderProfitGoal( $data )
{
	if( 	
 		     $data['dividendpershare'][0] > 0
		AND  $data['dividendpershare'][1] > 0
		AND  $data['dividendpershare'][2] > 0
	  )
	{
		return 1;
	}
	else
	{
		return 0;
	}
}

?>

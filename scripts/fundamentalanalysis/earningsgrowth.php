<?php

//Is the growth of the company earnings accellerating?

function getEarningsGrowth( $data )
{
	if( 	
 		     $data['incomegrowth' ][1] > 0
		AND  $data['incomegrowth'][2] > 0
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

<?php

//Is the growth of the company earnings accellerating?

function getEarningsAccel( $data )
{
	if( 	
 		     $data['incomegrowth' ][1] > $data['incomegrowth'][2] 
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

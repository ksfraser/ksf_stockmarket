<?php
//20090807 KF
//Eventum #146 Alert on retractments
//Adding alerts to check for a price that has retracted a certain percentage in so many days

function alert-retractment( $symbol, $days, $percentage )
{
	require_once( 'retractment.php' );
	if ( $percentage < percentretractment( $symbol, $days ) )
		return 1;
	else
		return 0;
}

//echo alert-retractment( "INN-UN", 260, 10);

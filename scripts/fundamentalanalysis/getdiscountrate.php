<?php


function getdiscountrate( $year )
{
global $MODELDIR;
	$bonddate = (string)($year + 30) . "-01-01";
	require_once( $MODELDIR . '/bondrate.class.php' );
	require_once( $MODELDIR . '/include_all.php' );
	$bondrate = new bondrate();
	$bondrate->where = "calendaryear = '" . $bonddate . "'";
	$bondrate->Select();
	if( isset( $bondrate->resultarray[0]['bondrate']) AND  $bondrate->resultarray[0]['bondrate'] > 7 )
	{
        	$discountrate = $bondrate->resultarray[0]['bondrate'] + 3;
	}
	else
	{
       	 	$discountrate = "10";
	}
	return $discountrate;
}

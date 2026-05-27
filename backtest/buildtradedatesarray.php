<?php

//20090804 KF
//Build an array of tradedates, and their next trade date.  Used in backtesting

function buildtradedatesarray( $startdate = "1970-01-01" )
{
	require_once( '../model/tradedates.class.php' );
	$tradedates = new tradedates();
	$tradedates->where = "tradedates > '" . $startdate . "'";
	$tradedates->orderby = "tradedates";
	$tradedates->Select();
	$prevdate = $startdate;
	foreach( $tradedates->resultarray as $row )
	{
		$tradedatesarray[$prevdate] = $row['tradedates'];
		$prevdate = $row['tradedates'];
	}
	return $tradedatesarray;
}

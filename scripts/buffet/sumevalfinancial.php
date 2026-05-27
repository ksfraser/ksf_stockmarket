<?php

/***************************************************
*
*	Calculates the score for these tenets
*
*	Added to codemeta as calcsummary 20091023
*		Bug 228 - retainearningsmv not a known column in the query (wrong table in query)
*		Bug 182 - retainearningsmv not a known column in the query (wrong table in query)
*
***************************************************/

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( '../../model/evalfinancial.class.php' );

//20091023
$summary = new evalfinancial();
$summary->calcsummary();

/*
$eval = new evalfinancial();
$eval->Select();
foreach ($eval->resultarray as $result )
{
	$update['idevalfinancial'] = $result['idevalfinancial'];
	$update['summary'] = $result['retainearningsmv'] + $result['roe'] + $result['lowcost'];
	if ( $result['debtratio'] < $result['acceptabledebt'] )
		$update['summary'] += 1;
	$eval->Update( $update );
}
*/

?>

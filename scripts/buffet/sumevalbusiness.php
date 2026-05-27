<?php

/******************************************
*
*	Sums up the scores for all rows
*	in evalbusiness.
*	Added into codemeta as calcsummary 20091023
*
******************************************/

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( '../../model/evalbusiness.class.php' );

//20091023
$summary = new evalbusiness();
$summary->calcsummary();

/* 20091023 KF
$eval = new evalbusiness();
$eval->Select();
foreach ($eval->resultarray as $result )
{
	$update['idevalbusiness'] = $result['idevalbusiness'];
	$update['summary'] = $result['simple'] + $result['neededproduct'] + ( 1 - $result['regulated'] ) + ( $result['noclosesubstitute'] ) + $result['cosnsistanthistory'];
	$eval->Update( $update );
}
*/

?>

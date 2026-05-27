<?php

/************************************************
*
*	Calculate the score of these tenets
*
*	added to codemeta as calcsummary 20091023
*
**************************************************/

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( '../../model/evalmanagement.class.php' );

//20091023
$summary = new evalmanagement();
$summary->calcsummary();
/*

$eval = new evalmanagement();
$eval->Select();
foreach ($eval->resultarray as $result )
{
	$update['idevalmanagement'] = $result['idevalmanagement'];
	$update['summary'] = $result['managementowners'] + $result['benefitreinvest'] + ( 1 - $result['expandbypurchase'] ) + ( 1 - $result['mimiccompetition'] ) + ( 1 - $result['hyperactivity'] ) + $result['cosnsistanthistory'] + $result['communicatemorethangaap'] + $result['publicconfession'] + ( 1 - $result['frfeqreorg'] );
	$eval->Update( $update );
}
*/



?>

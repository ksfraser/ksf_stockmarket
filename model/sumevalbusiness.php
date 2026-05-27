<?php

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( 'evalbusiness.class.php' );

$eval = new evalbusiness();
$eval->Select();
foreach ($eval->resultarray as $result )
{
	$update['idevalbusiness'] = $result['idevalbusiness'];
	$update['summary'] = $result['simple'] + $result['neededproduct'] + ( 1 - $result['regulated'] ) + ( $result['noclosesubstitute'] ) + $result['cosnsistanthistory'];
	$eval->Update( $update );
}


?>

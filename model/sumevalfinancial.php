<?php

//20111129 KF This script is in scripts/buffet
echo "Please run the version of this script in scripts/buffet";
exit();

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( 'evalfinancial.class.php' );

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


?>

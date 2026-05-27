<?php


//echo "CONTROLLER include generictable<br />";
	require_once( 'data/generictable.php');
//echo "Controller include local";
	require_once( '../local.php' );
	Local_Init();
	require_once( 'security/genericsecurity.php');
	$table = NULL;
	require_once( 'view/class.genericpage.php');
	$page = new genericpage();
	$page->SetItem( $Security->AddMenu() );
	
	$page->Display();
	return;

?>

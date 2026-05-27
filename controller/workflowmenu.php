<?php


//echo "CONTROLLER include generictable<br />";
	require_once( 'data/generictable.php');
//echo "Controller include local";
	require_once( '../local.php' );
	Local_Init();
	require_once( 'security/genericsecurity.php');
	global $Security;
	//var_dump($_GET);
	$table = NULL;
	//debug_print_backtrace();
	//echo "Call Genericpage<br />";
	require_once( 'view/class.genericpage.php');
	$page = new genericpage();
	require_once( 'workflow/workflow.php');
	//debug_print_backtrace();
	$workflow = new workflow( $table );
	if ($workflow)
		$page->SetItem( $workflow->Menu() );
	$workflow = new WorkflowMenu;
	//debug_print_backtrace();
	$page->SetItem( $workflow );
	$page->Display();
	//var_dump( $_SERVER );
	return;

?>

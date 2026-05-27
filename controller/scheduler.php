<?php

	require_once( 'data/generictable.php' );
	require_once( '../local.php' );
	Local_Init();
	//Logging
/*
 	include_once ( 'Log.php' );
        include_once ( 'Log/file.php' );
        $conf = array();
        $logobject = new Log_file( __FILENAME__ . "_debug_log.txt", "", NULL, PEAR_LOG_DEBUG );
        $logobject->log( "Controller launched" );
*/
	$modeldir = getcwd() . "/../model";
	require_once( 'jobspool/jobspool.php' );
	$sched = new scheduler();
	exit;
?>

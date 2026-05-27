<?php

/**********************************************************************************
*
*	This script checks the last update timestamp (asofdate)
*	for a stock and determines which ones haven't been updated
*	in the last X (argv[1]) days.
*
*	Only checks stocks that have the active flag set - no point in checking
*	decomissioned stock symbols.
*
*********************************************************************************/

echo __FILE__;

require_once( 'include_all.php' );
//require_once( 'data/generictable.php');
//require_once( '../local.php' );
//Local_Init();
//require_once( 'security/genericsecurity.php');
//global $Security;

//require_once( $MODELDIR . '/evalmarket.class.php' );
//require_once( $MODELDIR . '/bondrate.class.php' );

require_once( 'alerts.php' );

require_once( $MODELDIR . '/stockinfo.class.php' );


        $dateofInterest = date("Y-m-d", time() - ((int)$argv[1] * 24 * 60 * 60));
//	echo "Date: $dateofInterest\n";
        $stock = new stockinfo();
        //$stock->where = "asofdate < '" . $dateofInterest . "' and active = '1'";
        $stock->where = "reviseddate < '" . $dateofInterest . "' and active = '1'";
//	var_dump( $stock->where);
        $stock->Select();
	foreach( $stock->resultarray as $row )
	{
//		var_dump( $row );
//		sleep(5);
/*20130904 KF altered asofdate to reviseddate*/
		if( "CASH" <> $row['stockinfo'] )
		{
                	$subject = $row['corporatename'] . "(" . $row['idstockinfo'] . ")" . "'s last update in stockinfo was " . $row['reviseddate'] . " which is older than $dateofInterest (alert value " . $argv[1] . ")\n";
                	$header = "ACTION Stock Alert NO RECENT UPDATE for " . $row['corporatename'] . " in STOCKINFO \n";
                	$emailresult = EmailAlert( $argv[2], $header, $subject );
		}
        }
        exit;




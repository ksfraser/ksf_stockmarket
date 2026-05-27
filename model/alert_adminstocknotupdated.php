<?php

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( 'evalmarket.class.php' );
require_once( 'bondrate.class.php' );

require_once( 'alerts.php' );

require_once( 'stockinfo.class.php' );


        $dateofInterest = date("Y-m-d", time() - ((int)$argv[1] * 24 * 60 * 60));
//	echo "Date: $dateofInterest\n";
        $stock = new stockinfo();
        $stock->where = "asofdate < '" . $dateofInterest . "'";
//	var_dump( $stock->where);
        $stock->Select();
	foreach( $stock->resultarray as $row )
	{
//		var_dump( $row );
		sleep(5);
                $subject = $row['corporatename'] . "'s last update was " . $row['asofdate'] . " which is older than $dateofInterest (alert value " . $argv[1] . ")\n";
                $header = "ACTION Stock Alert NO RECENT UPDATE for " . $row['corporatename'] . "\n";
                $emailresult = EmailAlert( $argv[2], $header, $subject );
        }
        exit;

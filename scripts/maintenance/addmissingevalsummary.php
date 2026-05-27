<?php

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

include_once( '../../model/evalsummary.class.php' );
$evalsummary = new evalsummary();
$evalsummary->querystring = "insert into evalsummary (idstockinfo) select idstockinfo from stockinfo where not exists (select idstockinfo from evalsummary where stockinfo.idstockinfo = evalsummary.idstockinfo)";
$evalsummary->GenericQuery();

?>

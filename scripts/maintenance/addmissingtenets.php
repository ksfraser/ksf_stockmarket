<?php

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

include_once( '../../model/tenets.class.php' );
$tenets = new tenets();
$tenets->querystring = "insert into tenets (stocksymbol) select stocksymbol from stockinfo where not exists (select stocksymbol from tenets where stockinfo.stocksymbol = tenets.stocksymbol)";
$tenets->GenericQuery();

?>

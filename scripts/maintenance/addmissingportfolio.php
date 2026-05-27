<?php
//After a new stock is purchased by a user, add it into the user's portfolio.

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

include_once( '../../model/portfolio.class.php' );
$portfolio = new portfolio();
$portfolio->querystring = "insert into portfolio (stocksymbol, username) SELECT stocksymbol, username FROM transaction WHERE NOT EXISTS ( SELECT stocksymbol FROM portfolio WHERE transaction.stocksymbol = portfolio.stocksymbol) GROUP BY stocksymbol ORDER BY stocksymbol ";
$portfolio->GenericQuery();

?>

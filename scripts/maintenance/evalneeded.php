<?php

//Find the list of stocks in stockinfo that haven't been evaluated recently

require_once( 'data/generictable.php');
require_once( '../../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;
global $MODELDIR;
require_once( $MODELDIR . '/evalmarket.class.php' );
require_once( $MODELDIR . '/bondrate.class.php' );

require_once( $MODELDIR . '/alerts.php' );

require_once( $MODELDIR . '/evalbusiness.class.php' );
require_once( $MODELDIR . '/evalfinancial.class.php' );
require_once( $MODELDIR . '/evalmanagement.class.php' );
require_once( $MODELDIR . '/evalmarket.class.php' );

$bus = new evalbusiness();
$fin = new evalfinancial();
$man = new evalmanagement();
$market = new evalmarket();


$market->querystring = "SELECT e.idstockinfo, s.stocksymbol, s.corporatename, e.lasteval FROM evalmarket e, stockinfo s where e.lasteval < DATE_SUB(now(), INTERVAL 90 day) and e.idstockinfo=s.idstockinfo group by s.corporatename";

$man->querystring = "SELECT e.idstockinfo, s.stocksymbol, s.corporatename, e.lasteval FROM evalmanagement e, stockinfo s where e.lasteval < DATE_SUB(now(), INTERVAL 90 day) and e.idstockinfo=s.idstockinfo group by s.corporatename";

$fin->querystring = "SELECT e.idstockinfo, s.stocksymbol, s.corporatename, e.lasteval FROM evalfinancial e, stockinfo s where e.lasteval < DATE_SUB(now(), INTERVAL 90 day) and e.idstockinfo=s.idstockinfo group by s.corporatename";

$bus->querystring = "SELECT e.idstockinfo, s.stocksymbol, s.corporatename, e.lasteval FROM evalbusiness e, stockinfo s where e.lasteval < DATE_SUB(now(), INTERVAL 90 day) and e.idstockinfo=s.idstockinfo group by s.corporatename";

$market->GenericQuery();
$bus->GenericQuery();
$fin->GenericQuery();
$man->GenericQuery();

$mailmsg = "We need your help.  Please assist by evaluating some of the following stocks\n";
foreach( $market->resultarray as $res )
{
	$mailmsg .= $res['corporatename'] . " needs to be evaluated for market tenets\n";
}
foreach( $fin->resultarray as $res )
{
	$mailmsg .= $res['corporatename'] . " needs to be evaluated for financial tenets\n";
}
foreach( $bus->resultarray as $res )
{
	$mailmsg .= $res['corporatename'] . " needs to be evaluated for business tenets\n";
}
foreach( $man->resultarray as $res )
{
	$mailmsg .= $res['corporatename'] . " needs to be evaluated for management tenets\n";
}

$mailmsg .= "\n\nThe evaluations can be completed at http://silverdart.no-ip.org:8080\nThanks for your assistance\n";
$header = "Stock Tool requires your assistance";

require_once( $MODELDIR . '/users.class.php' );
$users = new users();
$users->where = "roles_id=1";
//$users->where = "roles_id=2";
$users->Select();
foreach( $users->resultarray as $res )
{
	EmailAlert( "fraser.ks@gmail.com", $header, $mailmsg );
	EmailAlert( $res['username'], $header, $mailmsg );
}
//echo $mailmsg;

?>

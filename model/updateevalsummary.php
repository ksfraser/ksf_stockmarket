<?php

require_once( 'include_all.php' );
//This script will grab the sums of the summaries for each of the tenets for a given stock

require_once( 'evalbusiness.class.php' );
require_once( 'evalfinancial.class.php' );
require_once( 'evalmarket.class.php' );
require_once( 'evalmanagement.class.php' );
require_once( 'evalsummary.class.php' );

$business = new evalbusiness();
$market = new evalmarket();
$management = new evalmanagement();
$financial = new evalfinancial();
$summary = new evalsummary();

$business->select = "avg(summary) as summary, idstockinfo";
$business->groupby = "idstockinfo";
$business->where = "lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)";
$management->select = "avg(summary) as summary, idstockinfo";
$management->groupby = "idstockinfo";
$management->where = "lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)";
$financial->select = "avg(summary) as summary, idstockinfo";
$financial->groupby = "idstockinfo";
$financial->where = "lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)";

$business->Select();
$market->Select();
$management->Select();
$financial->Select();
$summary->Select();

foreach( $management->resultarray as $res )
{
	$update[$res['idstockinfo']]['managementscore'] = $res['summary'];
}
foreach( $business->resultarray as $res )
{
	$update[$res['idstockinfo']]['businessscore'] = $res['summary'];
}
foreach( $financial->resultarray as $res )
{
	$update[$res['idstockinfo']]['financialscore'] = $res['summary'];
}
foreach( $market->resultarray as $res )
{
	$update[$res['idstockinfo']]['marginsafety'] = $res['marginsafety'];
}

//var_dump( $update );

foreach( $summary->resultarray as $res )
{
	$sumupdate['idstockinfo'] = $res['idstockinfo'];
	if( !isset( $update[$res['idstockinfo']]['marginsafety'] ) )
	{
		$update[$res['idstockinfo']]['marginsafety'] = -9999;
	}
	$sumupdate['marginsafety'] = $update[$res['idstockinfo']]['marginsafety'];
	if( !isset( $update[$res['idstockinfo']]['financialscore'] ) )
	{
		$update[$res['idstockinfo']]['financialscore'] = -1;
	}
	$sumupdate['financialscore'] = $update[$res['idstockinfo']]['financialscore'];
	if( !isset( $update[$res['idstockinfo']]['businessscore'] ) )
	{
		$update[$res['idstockinfo']]['businessscore'] = -1;
	}
	$sumupdate['businessscore'] = $update[$res['idstockinfo']]['businessscore'];
	if( !isset( $update[$res['idstockinfo']]['managementscore'] ) )
	{
		$update[$res['idstockinfo']]['managementscore'] = -1;
	}
	$sumupdate['managementscore'] = $update[$res['idstockinfo']]['managementscore'];
	$sumupdate['totalscore'] = 0;
	if ( $sumupdate['financialscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['financialscore'];
	if ( $sumupdate['businessscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['businessscore'];
	if ( $sumupdate['managementscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['managementscore'];
//	var_dump( $sumupdate );
	$summary->Update( $sumupdate );
}


?>

<?php

//20090626 KF
/*
	causing to exit seeing as this runs forever, 
	and having the DB do the work (query at bottom) 
	works a lot faster
*/
/*20091023 KF Added into codemeta as calcsummary*/
require_once( '../include_all.php' );
require_once( '../../model/evalsummary.class.php' );
$summary = new evalsummary();
$summary->calcsummary();
exit;

//This script will grab the sums of the summaries for each of the tenets for a given stock

require_once( '../../model/evalbusiness.class.php' );
require_once( '../../model/evalfinancial.class.php' );
require_once( '../../model/evalmarket.class.php' );
require_once( '../../model/evalmanagement.class.php' );
require_once( '../../model/evalsummary.class.php' );
require_once( '../../model/ratios.class.php' );
require_once( '../../model/iplace_calc.class.php' );

$business = new evalbusiness();
$market = new evalmarket();
$management = new evalmanagement();
$financial = new evalfinancial();
$summary = new evalsummary();
$ratios = new ratios();
$iplace_calc = new iplace_calc();

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

$ratios->select = "avg(attractivesum) as score, idstockinfo";
$ratios->groupby = "idstockinfo";
$ratios->where = "updateddate > DATE_SUB(current_date, INTERVAL 31 DAY)";
$ratios->Select();

$iplace_calc->select = "avg(score) as score, idstockinfo";
$iplace_calc->groupby = "idstockinfo";
$iplace_calc->where = "updateddate > DATE_SUB(current_date, INTERVAL 31 DAY)";
$iplace_calc->Select();

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
foreach( $ratios->resultarray as $res )
{
	$update[$res['idstockinfo']]['ratioscore'] = $res['score'];
}
foreach( $iplace_calc->resultarray as $res )
{
	$update[$res['idstockinfo']]['iplacecalcscore'] = $res['score'];
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
	if( !isset( $update[$res['idstockinfo']]['ratioscore'] ) )
	{
		$update[$res['idstockinfo']]['ratioscore'] = -1;
	}
	if( !isset( $update[$res['idstockinfo']]['iplacecalcscore'] ) )
	{
		$update[$res['idstockinfo']]['iplacecalcscore'] = -1;
	}
	$sumupdate['managementscore'] = $update[$res['idstockinfo']]['managementscore'];
	$sumupdate['totalscore'] = 0;
	if ( $sumupdate['financialscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['financialscore'];
	if ( $sumupdate['businessscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['businessscore'];
	if ( $sumupdate['managementscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['managementscore'];
	if ( $sumupdate['ratioscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['ratioscore'];
	if ( $sumupdate['iplacecalcscore'] > 0 )
	  	$sumupdate['totalscore'] += $sumupdate['iplacecalcscore'];
//	var_dump( $sumupdate );
	$summary->Update( $sumupdate );
}

/*
select avg(b.summary) as businessscore,
  b.idstockinfo
from evalbusiness b
where b.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and b.summary >= 0
group by b.idstockinfo

select avg(f.summary) as financialscore,
  f.idstockinfo
from evalfinancial f
where f.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and f.summary >= 0
group by f.idstockinfo

select avg(m.summary) as managementscore,
  m.idstockinfo
from evalmanagement m
where m.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and m.summary >= 0
group by m.idstockinfo

select avg(r.attractivesum) as ratioscore,
  r.idstockinfo
from ratios r
where r.updateddate > DATE_SUB(current_date, INTERVAL 90 DAY)
group by r.idstockinfo

select avg(i.score) as iplacecalcscore,
  i.idstockinfo
from iplace_calc i
where i.updateddate > DATE_SUB(current_date, INTERVAL 90 DAY)
group by idstockinfo
  *****************************************************************
UPDATE evalsummary e
set e.businessscore =
(select avg(b.summary) as businessscore
from evalbusiness b
where b.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and b.summary >= 0
  and b.idstockinfo = e.idstockinfo
group by b.idstockinfo
),
e.financialscore =
(select avg(f.summary) as financialscore
from evalfinancial f
where f.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and f.summary >= 0
  and f.idstockinfo = e.idstockinfo
group by f.idstockinfo
),
e.managementscore =
(select avg(m.summary) as managementscore
from evalmanagement m
where m.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and m.summary >= 0
  and m.idstockinfo = e.idstockinfo
group by m.idstockinfo),
e.iplacecalcscore =
(select avg(i.score) as iplacecalcscore
from iplace_calc i
where i.updateddate > DATE_SUB(current_date, INTERVAL 90 DAY)
group by idstockinfo),
e.ratioscore =
(select avg(r.attractivesum)
  from ratios r
where r.updateddate > DATE_SUB(current_date, INTERVAL 90 DAY)
and r.idstockinfo = e.idstockinfo
group by r.idstockinfo),
e.marginsafety =
(select avg(m.marginsafety)
  from evalmarket m
where m.lasteval > DATE_SUB(current_date, INTERVAL 90 DAY)
  and e.idstockinfo=m.idstockinfo
 group by m.idstockinfo)

update evalsummary set totalscore = ratioscore + iplacecalcscore + businessscore + financialscore + managementscore
*/
?>



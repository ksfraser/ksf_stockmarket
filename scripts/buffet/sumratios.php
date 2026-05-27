<?php

//Sum up the "attractive" scores into attractivesum
//Added to codemeta as calcsummary 20091023

require_once( '../../model/include_all.php' );
require_once( '../../model/ratios.class.php' );

//20091023
$summary = new ratios();
$summary->calcsummary();
/*

$ratios = new ratios();

$ratios->querystring = "update ratios set attractivesum = attractiveroa + attractiveroce + attractivegross + attractivepretax + attractivenet + roeattractive + lowcost + sustaindebtratio";
$ratios->GenericQuery();
*/

?>

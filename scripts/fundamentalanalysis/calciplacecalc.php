<?php

//Calculate the iplace values
/*
  	var $iplace_calc;
         var $earningsgrowth;
         var $earningsaccel;
         var $pe;
         var $tradingvolume;
         var $institutioninterest;
         var $orderimbalance;
         var $shortinterest;
         var $volatility;
         var $idstockinfo;
         var $dividendearningratio;
         var $extracash;
         var $shareholderprofitgoal;
         var $dividendincreases;
         var $score;
*/
define( 'MODELDIR', '/mnt/2/development/var/www/html/finance/model' );
require_once( MODELDIR . '/include_all.php' );


require_once( MODELDIR . '/iplace_calc.class.php' );
$iplace = new iplace_calc();

require_once( 'getlastfin_statement.php' );
$lastfinarray = getlastfin_statement();


$iplace->querystring = "update iplace_calc set score = 
         earningsgrowth + 
         earningsaccel + 
         tradingvolume + 
         institutioninterest + 
         orderimbalance + 
         shortinterest + 
         volatility + 
         dividendearningratio + 
         extracash + 
         shareholderprofitgoal + 
         dividendincreases ";

$iplace->GenericQuery(); 


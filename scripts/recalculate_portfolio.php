<?php
echo __FILE__;

//Recalculate portfolio values
require_once( '../model/include_all.php' );
require_once( '../model/portfolio.class.php' );
$portfolio = new portfolio();

/************************************************************
* 20110122 KF Moved the list of indv fcns below into UpdatePortfolios
$portfolio->Insertstockuserlist();
$portfolio->Updatebookvalue();
$portfolio->Updatedividendbookvalue();
$portfolio->Updatenumbershares();
$portfolio->Updatecurrentprice();
$portfolio->Updatemarketvalue();
$portfolio->Updateprofit();
$portfolio->Updatemarketbook();
$portfolio->Updatedividendpershare();
$portfolio->Updateannualdividend();
$portfolio->Updatedividendpercentbookvalue();
$portfolio->Updatedividendpercentmarketvalue();
$portfolio->Updatedividendyield();
$portfolio->Updateyield();
$portfolio->Updatepercenttotalbookvalue();
$portfolio->Updatepercenttotalmarketvalue();
$portfolio->Updatepercenttotaldividend();
********************************************************/

$portfolio->UpdatePortfolios();


?>

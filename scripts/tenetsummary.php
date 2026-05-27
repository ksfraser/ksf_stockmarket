<?php

//This script will summarize the values for the tenets for the various stocks.

//20081226 Eventum project finance issue #28
//crontab maillog errors undefined variable table line 21

echo __FILE__;

require_once('view/view.include.php');
require_once('data/generictable.php');
require_once('../local.php');
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
{
        global $smarty;
}
$menu = Local_Menu();
require_once( 'view/class.genericpage.php');
$page = new genericpage();
$page->SetItem( $Security->AddMenu() );
//Eventum issue #28 table not set
$page->SetItem($menu);
if( isset( $table ))
{
	require_once( 'workflow/workflow.php');
	$workflow = new workflow( $table );
	if ($workflow)
    		$page->SetItem( $workflow->Menu() );
	$workflow = new WorkflowMenu;
	$page->SetItem( $workflow );
}
//!#28
//$table = stockinfo;
$page->SetItem($page->SearchForm());
        
	require_once( $MODELDIR . '/evalfinancial.class.php');
	require_once( $MODELDIR . '/evalmarket.class.php');
	require_once( $MODELDIR . '/evalmanagement.class.php');
	require_once( $MODELDIR . '/evalbusiness.class.php');
	require_once( $MODELDIR . '/stockinfo.class.php');
	require_once( $MODELDIR . '/ratios.class.php');
	require_once( $MODELDIR . '/iplace_calc.class.php');
	//Grab the latest of each

	$market = new evalmarket();
	$management = new evalmanagement();
	$financial = new evalfinancial();
	$business = new evalbusiness();
	$stock = new stockinfo();
	$ratios = new ratios();
	$iplace_calc = new iplace_calc();
	//Set which stock to look for - that stock only
	//var_dump( $_POST );
	//var_dump( $_GET );
	if( isset( $_GET['stocksymbol'] ))
	{
		$stock->where = "stocksymbol = '" . $_GET['stocksymbol'] . "'";
	}
	else if( isset( $_POST['searchstring'] ))
	{
		$stock->where = "stocksymbol = '" . $_POST['searchstring'] . "'";
		$stock->Search($_POST);
		//var_dump($stock->resultarray);
		foreach( $stock->resultarray as $company )
		{
			$stock->where .= " OR stocksymbol = '" . $company['stocksymbol'] . "'";
		}
	}
	$stock->Select();
	foreach( $stock->resultarray as $res )
	{
		$idstockinfo = $res['idstockinfo'];
		$corporatename = $res['corporatename'];
		$market->where = "idstockinfo = '" . $idstockinfo . "'";
		$management->where = "idstockinfo = '" . $idstockinfo . "'";
		$financial->where = "idstockinfo = '" . $idstockinfo . "'";
		$business->where = "idstockinfo = '" . $idstockinfo . "'";
		$ratios->where = "idstockinfo = '" . $idstockinfo . "'";
		$market->orderby = "lasteval desc";
		$management->orderby = "lasteval desc";
		$financial->orderby = "lasteval desc";
		$business->orderby = "lasteval desc";
		$ratios->orderby = "updateddate desc";
		$market->limit = "1";
		$management->limit = "1";
		$financial->limit = "1";
		$business->limit = "1";
		$ratios->limit = "1";
		$market->Select();
		$management->Select();
		$financial->Select();
		$business->Select();
		$ratios->Select();
		$iplace_calc->where = "idstockinfo = '" . $idstockinfo . "'";
		$iplace_calc->orderby = "updateddate desc";
		$iplace_calc->limit = "1";
		$iplace_calc->Select();
		$h2 = new atomic( $corporatename, "<h2>", "</h2>" ) ;
		$page->SetItem( $h2 );
/*
		$h2 = new atomic( "Company Info", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $res ) );
*/
		$h2 = new atomic( "Market Tenets", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $market ) );
		$h2 = new atomic( "Management Tenets", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $management ) );
		$h2 = new atomic( "Financial Tenets", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $financial ) );
		$h2 = new atomic( "Business Tenets", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $business ) );
		$h2 = new atomic( "Ratio Scores", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $ratios ) );
		$h2 = new atomic( "Investor Place calculated Scores", "<h3>", "</h3>" ) ;
		$page->SetItem( $h2 );
		$page->SetItem( $page->Array2Table( $iplace_calc ) );
	}
//$page->SetItem( $page->Array2Table( $market->resultarray ) );
//$page->SetItem( $page->Array2Table( $management->resultarray ) );
//$page->SetItem( $page->Array2Table( $financial->resultarray ) );
//$page->SetItem( $page->Array2Table( $business->resultarray ) );
$page->Display();
exit(0);


?>

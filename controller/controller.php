<?php
/***************************************************************************************
*20101228 KF
*       The program can be broken down into Model, View, Controller where
*               Model is responsible for getting the data and processing it
*               View is responsible for creating screens be it web or otherwise
*               Controller sits in the middle, determines what gets sent where
*                       Also would be responsible for security
*                       Also responsible for session/memory
*       In a non web app, there would be a certain program flow
*               INIT
*               LOOP taking in input, processing, display
*               EXIT
*       In a web app, the INIT also needs to include validating security and SESSION
*               EXIT needs to ensure session data is saved
*****************************************************************************************/

	require_once( 'data/generictable.php' );
	require_once( '../local.php' );
	Local_Init();
	require_once( 'security/genericsecurity.php' );
	global $Security;
/*
	require_once( 'data/userpref/userpref.php' );
	$up = new userspref();
*/
	//Logging
/*
 	include_once ( 'Log.php' );
        include_once ( 'Log/file.php' );
        $conf = array();
        $logobject = new Log_file( __FILENAME__ . "_debug_log.txt", "", NULL, PEAR_LOG_DEBUG );
        $logobject->log( "Controller launched" );
*/

	$prefarray = array();
	//var_dump( $prefarray );
	//var_dump( $Security->idusers );
//	if( include_once( 'userpref/apppref.php' ) == TRUE)
	include_once( 'apppref/apppref.php' );
		$apppref = new apppref( $Security->idusers, $prefarray );
	//var_dump( $apppref );
	if( isset( $apppref->prefarray ))
	{
		$prefarray = $apppref->prefarray;
	}
	else
	{
		$prefarray = NULL;
	}
	//var_dump( $prefarray );
	if( isset( $prefarray['rows_per_page'] ) && !isset( $_GET['numberrows'] ))
		$_GET['numberrows'] = $prefarray['rows_per_page'];
	if( isset( $_GET['action'] ))
	{
		$act = $_GET['action'];
		$mode = $act;
	}
	if( isset( $_GET['table'] ))
	{
		$thisclass = $_GET['table'];
	}
	if (isset( $thisclass ) )
	{
		$classfile = $thisclass . ".class.php";
		$include_status = include_once( CLASSDIR . "/" . $classfile);
		if ($include_status == true)
		{
			$class = $thisclass;
			$table = new $class;
			if( isset( $_GET['startrows'] ))
				$table->startrows = $_GET['startrows'];
			else
				$table->startrows = NULL;
			if( isset( $_GET['numberrows'] ))
				$table->numberrows = $_GET['numberrows'];
			else
				$table->numberrows = NULL;
	//		echo __FILE__ . " Set Table.";
		}
		else
		{
			$table = NULL;
			$class = $thisclass;
			//$table = new $class;
	//		echo __FILE__ . ":" . __LINE__ . " DIDN'T Set Table.";
		}
	}
	else
	{
		$table = NULL;
		echo __FILE__ . ":" . __LINE__ . " DIDN'T Set Table.";
	}
	//debug_print_backtrace();
	if (!NOSMARTY)
	{
		global $smarty;
		if ($smarty)
		{
			$smarty->assign('callingpage', $table->querytablename);
		}
		//$Security->AddMenu($smarty);
	}	
	$menu = Local_Menu();
	require_once( 'view/class.genericpage.php');
	$page = new genericpage();
	if (defined('NOCACHE'))
		$page->SetNocache();
	$page->SetItem( $Security->AddMenu() );
	$page->SetItem($menu);
	require_once 'HTML/Menu.php';
	//$html_menu_tree = new HTML_Menu( $Security->html_menu, 'tree' );
	//$html_menu_tree->show();
	$html_menu_sitemap = new HTML_Menu( $Security->html_menu, 'sitemap' );
	$html_menu_sitemap->show();
	//$html_menu_rows = new HTML_Menu( $Security->html_menu, 'rows' );
	//$html_menu_rows->show();
	//$html_menu_urhere = new HTML_Menu( $Security->html_menu, 'urhere' );
	//$html_menu_urhere->show();
	//$html_menu_prevnext = new HTML_Menu( $Security->html_menu, 'prevnext' );
	//$html_menu_prevnext->show();
	//if( include_once( 'workflow/workflow.php') == TRUE )
	include_once( 'workflow/workflow.php');
	//{
		$workflow = new workflow( $table );
		if ($workflow)
			$page->SetItem( $workflow->Menu() );
		$workflowmenu = new WorkflowMenu;
		$page->SetItem( $workflowmenu );
	//}
	if (isset($mode))
	{
		$page->mode = $mode;
	} else if (isset($_GET['mode']))
	{
		$page->mode = $_GET['mode'];
	}
	if (count($_POST) > 1)
	{
		if ($_POST['formmode'] == "insert")
		{
			$status = $table->Insert($_POST);
			if ($status == SUCCESS)
			{
			} else
			{
			}
		} else if ($_POST['formmode'] == "update")
		{
			$table->Update($_POST);
		} else if ($_POST['formmode'] == "replace")
		{
			$table->Update($_POST);
		} else if ($_POST['formmode'] == "delete")
		{
			$table->_Delete($_POST);
		} 
		 else if ($_POST['formmode'] == "search")
		{
			$table->Search($_POST);
			$table->result = $table->rawresult;
		} 
	}
	else if ((isset($_GET['update'])) OR (isset($_GET['replace'])))
	{
	//	$table->Update($_GET);	
		$page->SetItem($page->InsertForm($table, $_GET));
	}
	else if (isset($_GET['delete']))
	{
		$table->_Delete($_GET);	
		header("Location: " . $_SERVER['PHP_SELF']);
	}
	else if( isset( $_GET['report'] ) )
	{
		//need to call the report handler
		//require_once( 'reports/report.php' );
		$image = new kf_image( 'reports/' . $_GET['report'] );
		$page->SetItem( $image );
	}
	if ($mode == "insert")
	{
		$page->SetItem($page->InsertForm($table));
	}
	else
	if ($mode == "list")
	{
		$page->PageAddTable($table);
		var_dump( $table->queries );
		//$page->SetItem($page->FieldDisplay( $table ));
	}
	else
	if ($mode == "replace")
	{
		$page->PageAddTable($table);
	}
	else
	if ($mode == "update")
	{
		$page->PageAddTable($table);
	}
	else
	if ($mode == "delete")
	{
		$page->PageAddTable($table);
	}
	else
	if ($mode == "search")
	{
		$page->SetItem($page->Array2Table($table));
		$page->SetItem($page->SearchForm());
		//$mode = "list"
		//$page->PageAddTable($table);
	}
	if (!NOSMARTY)
	{
		$smarty->assign('legacy', $page->Display() );
		$smarty->display('genericpage.tpl'); 
	} else
	{
		$page->Display();
	}
	return;
?>

<?php
	include('smarty/libs/Smarty.class.php');
	require_once('genericsecurity.php');
	$smarty = new Smarty;
	if (isset($_SESSION['menu']))
	{
		$menu = $_SESSION['menu'];
		$smarty->assign('menu', $menu);
	}
	

if(isset($_POST['register']))
{
	//called by this script
	require_once('users.class.php');
	$user = new users();
	$status = $user->Insert($_POST);
	$smarty->assign('showmsg', 'y');
	$smarty->assign('msg', "Insert Status: $status");
}
	
$smarty->assign('customfields', array(
			array ('prefName' => 'surname', 'Label' => 'Surname'), 
			array ('prefName' => 'firstname', 'Label' => 'First Name')
			)
		);	
		$smarty->assign('rnd_num_reg', 'y');
	
	$smarty->display('register.tpl');
?>

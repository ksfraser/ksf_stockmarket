<?php

if (isset( $_POST['test'] ) )
{
}
else
if (isset( $_GET['test'] ) )
{
}
else
{
	$thisclass = 'index';
	$mode = "index";
}
chdir( 'model/' );
require_once('controller/controller.php');
?>

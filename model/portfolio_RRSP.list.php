<?php
session_start();
$thisclass = 'portfolio_sub' ;
$mode = "list";
$_SESSION['accounttype'] = "RRSP";
$_SESSION['username'] = $_SERVER['PHP_AUTH_USER'];
/*
var_dump( $_SESSION );
sleep(5);
var_dump( $_SERVER );
sleep(5);
*/
require_once( '../controller/controller.php');
?>

<?php

//Create individual forms and classes from metadata

require_once('metadata.class.php');

$thispage = new my_metadata();
if (!isset($_POST['tablename']))
{
	$thispage->NewClass();
} else
{
	
	$thispage->NewFields($_POST['tablename'], $_POST['prettyname']);
}
$thispage->Display();

?>

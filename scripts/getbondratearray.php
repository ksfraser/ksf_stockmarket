<?php

function getbondratearray( $limit = '10' )
{
	global $MODELDIR;
	require_once( $MODELDIR . '/bondrate.class.php' );
	$bondrate = new bondrate();
	$bondrate->where = NULL;
	$bondrate->orderby = "calendaryear asc";
	$bondrate->limit = $limit;
	$bondrate->Select();
	return $bondrate->resultarray;
}


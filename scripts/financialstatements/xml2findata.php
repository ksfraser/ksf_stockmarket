<?php

//20090824 KF
//Convert XML data back to an array for further processing

function xml2findata( $string )
{
	var_dump( $string );
	$array = simplexml_load_string( $string );
	return $array;
}
function xmlfile2findata( $filename )
{
	$array = simplexml_load_file( $filename );
	return $array;
}

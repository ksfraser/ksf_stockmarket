<?php

//20090826 KF
//Findata2xml is producing XML
//but is not leaving us in a nice position for later

require_once( 'converttags.php' );
require_once( 'data/tableextractor.php' );

function findata2array( $filename, $anchor )
{

	$array = array();
$bad =  array( "<spanclass=chr>", ",", '<spanstyle="padding-left:18px;">', "<spanstyle=\"padding-left:18px;\"></span>", "</span>", '"<spanstyle="padding-left:18px;"></span>', '<spanstyle="padding-left:18px;"></span>' );
$good = array( "",                "",  "",                                 "",                                          ""       , "",                                         ""                                        );
        $fp = fopen( $filename, "r" );
	if( $fp == NULL )
		return $array;
        $data = fread( $fp, 1000000 );
        fclose( $fp );

        $tbl = new tableExtractor;
        $tbl->source = $data; // Set the HTML Document
        $tbl->anchor = $anchor; // Set an anchor that is unique and occurs before the Table
        //$tbl->anchor = 'annualdiv'; // Set an anchor that is unique and occurs before the Table
        $tpl->anchorWithin = true; // To use a unique anchor within the table to be retrieved
        $d = $tbl->extractTable(); // The array
        //var_dump( $d );

	if( is_array( $d ) )
	{
		foreach( $d as $dkey => $dvalue )
		{
			$count = 0;
			foreach( $dvalue as $rkey=>$value )
			{
				$count++;
				if( $count == 1 )
				{
					$key = converttags( $value );
				}
				else
				if( $count > 1 )
				{
					$array[$key][$count - 2] = str_replace( $bad, $good, $value);
				}
			}
		}
//	var_dump( $array );
	}

	return $array;
}

?>


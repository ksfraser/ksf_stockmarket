<?php

function getlastfin_statement()
{
	require_once( MODELDIR . '/include_all.php' );
	
	require_once( MODELDIR . '/stockinfo.class.php' );
	$stockinfo = new stockinfo();

	require_once( MODELDIR . '/fin_statement.class.php' );
	$fin_statement = new fin_statement();

	$stockinfo->Select();
	foreach( $stockinfo->resultarray as $row )
	{
        	//Each row is 1 stock
        	//Get the latest fin statement
        	$fin_statement->where = "idstockinfo = '" . $row['idstockinfo'] . "'";
        	$fin_statement->orderby = "lasteval desc";
        	$fin_statement->limit='1';
        	$fin_statement->Select();
/*
 	       var_dump( $fin_statement->resultarray );
        	sleep(5);
*/
		foreach( $row as $key=>$value )
		{
			$results[$key] = $value;
		}
		foreach( $fin_statement->resultarray[0] as $key=>$value )
		{
			$results[$key] = $value;
		}
		var_dump( $results );	
	}
	return $results;
}


//TEST
getlastfin_statement();

?>

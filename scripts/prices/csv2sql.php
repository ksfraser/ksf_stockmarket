<?php

//read in the yahoo csv
//parse and write sql inserts
function go( $filename )
{
	 $fp = fopen( $filename, "r" );
	if( NULL == $fp )
		return FAILURE;
	$symbol = strtok( $filename, "." );
	echo "Symbol: $symbol from filename $filename\n";
	$fpins = fopen( $symbol . date( 'Ymdhms' ) . ".sql", "w" );
	$count = 0;
         while( !feof( $fp ))
         {
                 $fields = fgetcsv( $fp, 1024 );
                 /* Yahoo CSV format:
                  *Date,
                  *Open,
                  *High,
                  *Low,
                  *Close,
                  *Volume,
                  *Adj Close
                  */
		if( $count > 0 )
		{
			$query = "insert ignore into stockprices ( date,  day_open, day_high, day_low,  day_close, volume,   adjustedclose, symbol ) values    ( '$fields[0]', '$fields[1]', '$fields[2]', '$fields[3]', '$fields[4]',  '$fields[5]', '$fields[6]', '$symbol' );";
			$query2 = "insert ignore into tradedates values( '$fields[0]' );";
			$query3 = "update stockprices  set day_open = '$fields[1]', day_high = '$fields[2]', day_low = ' $fields[3]',  day_close = '$fields[4]', volume = '$fields[5]',   adjustedclose = '$fields[6]' where symbol = '$symbol' and date = '$fields[0]'; "; 
			fwrite( $fpins, $query . "\n" );
			fwrite( $fpins, $query2 . "\n" );
		//	fwrite( $fpins, $query3 . "\n" );
		}
		$count++;
	}
	fclose( $fp );
	fclose( $fpins );
	echo "$count ROWS\n";
}

//var_dump( $argv );
go( $argv[1] );


?>

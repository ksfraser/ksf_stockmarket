<?php

//20090824 KF Eventum 166
//Refactor parse_finances.php

function googledownloadstatement( $stocksymbol, $exchange )
{
//TSE symbols need to be converted for on google
        $stocksymbol = str_replace( "-", ".", $stocksymbol );
        $exchangestock = $exchange . ":" . $stocksymbol;
	$dirname = BASEDIR . "/fin_reports/" . $stocksymbol . "/";
        $filename = $dirname . $stocksymbol . "-" . date( 'Ymd' ) . ".google.html";

//20090823 Google has changed its URL
//http://www.google.com/finance?q=NYSE:BNI&fstype=ii
        // WAS $url = "http://finance.google.com/finance?fstype=ci&q=" . $exchangestock . "&hl=en";
        $url = "http://www.google.com/finance?&q=" . $exchangestock . "&fstype=ii";
        $fp = fopen( $url, "r" );
        if( $fp )
        {
        	$data = "";
        	while (!feof($fp)) {
        	    $data .= @fread($fp, 1024);
		}
        	fclose($fp);
		//NEED TO CHECK THAT THE DIR EXISTS
		//ELSE MKDIR
		if( !is_dir( $dirname ))
		{
			//if a file is there with this name, don't overwrite
			if( !file_exists( $dirname ))
			{
				mkdir( $dirname, 0775 );
			}
			else
				return NULL;
		}
        	$fp2 = fopen( $filename, "w" );
		if( $fp2 != NULL )
		{
        		fwrite( $fp2, $data );
        		fclose( $fp2 ); 
        		return $filename;
		}
		else
			return NULL; //NEVER WANT TO GET HERE!
        }       
	else
		return NULL;
}

?>

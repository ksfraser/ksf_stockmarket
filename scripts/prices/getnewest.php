<?php

/*******************************************
*
*	This app is to query YAHOO for
*	the data of the stocks in the
*	stockprices database since the
*	last date of info we have for
*	them.  Really should check
*	for active only.  So far
*	the number of stocks in
*	the db doesn't make it an
*	issue.
*
****************************************/

require_once( '../../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );

include( $MODELDIR . '/stockprices.class.php' );
//include( $MODELDIR . '/stockinfo.class.php' );
//include( $MODELDIR . '/stockexchange.class.php' );
//include( 'view/class.genericpage.php' );
//require_once( $MODELDIR . '/tradedates.class.php' );
require_once( '../common/cleanstockprices.php' );
//require_once( 'common/webpage2txt.php' );
require_once( '../common/yahooexchanges.php' );
require_once( 'queryyahoo.php' );

//global $APPDIR;

function getnewest( $flog, $thisex )
{
/*20090705 KF
*We will also have the case of this hasn't been run for
*a few days so the latest entries aren't here. We will
*need to do the opposite - find the latest and use that
*as the start dates.
*/
global $APPDIR;
	fwrite( $flog, "\n\nSTARTING download of newest data\n" );
	cleanstockprices();
	$stockprices = new stockprices();
	$stockprices->querystring = "
	SELECT p.symbol as stocksymbol, max( p.date ) as date, 
	YEAR(max( p.date )) as year, MONTH(max( p.date )) as month, DAY(max( p.date )) as day, 
	i.stockexchange as stockexchange, i.idstockinfo as idstockinfo
	FROM stockprices p, stockinfo i
	where p.symbol = i.stocksymbol
	 	and i.active = '1'
	GROUP BY p.symbol";
	
	$stockprices->GenericQuery();
	echo "Processing " . count( $stockprices->resultarray ) . "Stock symbols";
	foreach( $stockprices->resultarray as $key => $value )
	{
	//	var_dump( $value );
		$symbol = $value['stocksymbol'];
		$idstockinfo = $value['idstockinfo'];
		fwrite( $flog, "If Symbol " . $symbol . ", Year " . $value['year'] . " Month " . $value['month'] . " less than or equal to " . date( 'Y' ) .  " " . date( 'm' ) . ".  Download!\n");
		$gonew = "no";
		//Eliminate cash and testing symbols
		if ( 	( $symbol != 'CASH' )
 			AND ( $symbol != 'BOO' )
                        AND ( $symbol != 'ZZZ' )
		)

		{
			if ($value['year'] < date( 'Y' ) )
			{
				$gonew = "yes";
			}
			else  
			if ($value['year'] = date( 'Y' ) )
			{
				if ($value['month'] < date( 'm' ) )
				{
						$gonew = "yes";
				}
				else 
				if ($value['month'] = date( 'm' ) )
				{
					if ($value['day'] < date( 'd' ) )
					{
						$gonew = "yes";
					}
					else
					{
						$gonew = "no";
					}
					
				}
				else
				{
					$gonew = "no";
				}
			}	
			else
			{
				$gonew = "no";
			}
		}
		if ($gonew == "yes")		
		{
			fwrite( $flog, "Downloading $symbol\n" );
			$filename = QueryYahoo( $symbol, $thisex[ $value['stockexchange' ] ] 
						,$value['year'], date( 'Y' ),
						$value['month'] , date( 'm' ),
						$value['day'] , date( 'd' ),
						$flog
						);
			//extractinsert( $flog, $filename, $symbol, $value );
		}
		cleanstockprices();
	}
	unset( $gonew );
	unset( $stockprices );
	return SUCCESS;
}

$flog = fopen( $APPDIR . "/logs/getnewest" . date( 'Ymdhs' ) . ".txt", "w" );
fwrite( $flog, "Started run" );

//Define some constants
$const_YEAR = "1970";
$const_MONTH = "1";
$const_DAY = "01";

$thisex = yahooexchanges();
getnewest( $flog, $thisex );
fclose( $flog );

?>

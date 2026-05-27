<?php


require_once( '../../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
include( '../../model/fxprices.class.php' );
$fxprices = new fxprices();
include( 'view/class.genericpage.php' );
$page = new genericpage();
$page->mode = "search";
$menu = $Security->AddMenu();
$page->SetItem( $menu );


//UBC only returns 3 years worth daily.  Otherwise they come back monthly

/* Only use the following for adding new currency pairs*/
// define( 'NEW', 1 );
if( defined( 'NEW' ))
{
	$currency="CAD";
	$foreigncurrency="CHF";
	$filename = QueryUBC( $currency, $foreigncurrency
				,"2006", date( 'Y' ), 
				"1", date( 'm' ), 
				"01", date( 'd' ) 
				);
	echo $filename;
	$fp = fopen( $filename, "r" );
	while( !feof( $fp ))
	{
		$fields = fgetcsv( $fp, 1024 );
		/* UBC CSV format:
		*Julien Date
		*Date,
		*Week Day,
		*Exchange Rate
		*/
		if( count( $fields ) == 4 and $fields[0] != "Jul.Day" )
		{
			$insert['date'] = $fields[1];
			$insert['day_close'] = $fields[3]; 
			$insert['currency'] = $currency;
			$insert['foreigncurrency'] = $foreigncurrency;
			if( $insert['date'] != NULL )
				$fxprices->Insert( $insert );
		}
	}
}

/*20090705 KF
*What about the currencies that were partially inserted because 
*the memory of the server was tapped out and the mysql
*process terminated?  We need to go and find the first
* entry (oldest) since the csv files are newest at the
*top which means the newest get entered.  Use the oldest
*as the end dates against 1980.
*/
$fxprices->querystring = "delete from fxprices where day_close = '0' and day_high = '0'";
$fxprices->GenericQuery();
$fxprices->querystring = "
SELECT currency, foreigncurrency, min( date ), 
YEAR(min( date )) as year, MONTH(min( date )) as month, DAY(min( date )) as day 
FROM fxprices 
GROUP BY currency, foreigncurrency";

$fxprices->GenericQuery();
foreach( $fxprices->resultarray as $key => $value )
{
	//UBC has data after 1971
	if ( $value['currency'] != 'CASH' AND $value['year'] > 1974 )
	{
		$filename = QueryUBC( $value['currency'], $value['foreigncurrency'],
					$value['year'] - 3, $value['year'], 
					$value['month'], $value['month'],
					$value['day'], $value['day'] - 1
					);
//		echo $filename;
//		sleep( 2 );
		$fp = fopen( $filename, "r" );
		while( !feof( $fp ))
		{
			$fields = fgetcsv( $fp, 1024 );
			//var_dump( $fields );
			if( count( $fields ) == 4 and $fields[0] != "Jul.Day" )
			{
				$insert['date'] = $fields[1];
				$insert['day_close'] = $fields[3]; 
				$insert['currency'] = $value['currency'];
				$insert['foreigncurrency'] = $value['foreigncurrency'];
				if( $insert['date'] != NULL )
					$fxprices->Insert( $insert );
			}
		}
	}
}

/*20090705 KF
*We will also have the case of this hasn't been run for
*a few days so the latest entries aren't here. We will
*need to do the opposite - find the latest and use that
*as the start dates.
*/

$fxprices->querystring = "delete from fxprices where day_close = '0' and day_high = '0'";
$fxprices->GenericQuery();
$fxprices->querystring = "
SELECT currency, foreigncurrency, max( date ), 
YEAR(max( date )) as year, MONTH(max( date )) as month, DAY(max( date )) as day 
FROM fxprices 
GROUP BY currency, foreigncurrency";

$fxprices->GenericQuery();
foreach( $fxprices->resultarray as $key => $value )
{
//	var_dump( $value );
	if ( $value['currency'] != 'CASH' )
	{
		$filename = QueryUBC( $value['currency'], $value['foreigncurrency']
					,$value['year'], date( 'Y' ),
					$value['month'], date( 'm' ),
					$value['day'] + 1, date( 'd' )
					);
//		echo $filename;
//		sleep( 2 );
		$fp = fopen( $filename, "r" );
		while( !feof( $fp ))
		{
			$fields = fgetcsv( $fp, 1024 );
			$insert['date'] = $fields[1];
			$insert['day_close'] = $fields[3]; 
			$insert['currency'] = $value['currency'];
			$insert['foreigncurrency'] = $value['foreigncurrency'];
			if( $insert['date'] != NULL )
				$fxprices->Insert( $insert );
		}
	}
$fxprices->querystring = "delete from fxprices where day_close = '0' and day_high = '0'";
$fxprices->GenericQuery();
}

?>

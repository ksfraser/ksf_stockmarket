<?php


/*******************************************************
*
*
*******************************************************/

require_once( '../../local.php' );
require_once( '../common/EmailAlert.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'data/generictable.php' );
require_once( 'queryubc.php' );
include( '../../model/fxprices.class.php' );
$fxprices = new fxprices();
include( 'view/class.genericpage.php' );
$page = new genericpage();
$page->mode = "search";
$menu = $Security->AddMenu();
$page->SetItem( $menu );


//UBC only returns 3 years worth daily.  Otherwise they come back monthly



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
	if( 	    $value['year'] == date( 'Y' )
		AND $value['month'] == date( 'm' )
		AND $value['day'] == date( 'd' )
	)
	{
		//We've already downloaded to today
		exit(0);
	}

		$filename = QueryUBC( $value['currency'], $value['foreigncurrency']
					,$value['year'], date( 'Y' ),
					$value['month'], date( 'm' ),
					$value['day'] + 1, date( 'd' )
					);
		$fp = fopen( $filename, "r" );
		$linecount = 0;
		while( !feof( $fp ))
		{
			$fields = fgetcsv( $fp, 1024 );
			if( isset( $fields[3] ))
			{
				$insert['date'] = $fields[1];
				$insert['day_close'] = $fields[3]; 
				$insert['currency'] = $value['currency'];
				$insert['foreigncurrency'] = $value['foreigncurrency'];
				if( $insert['date'] != NULL )
					$fxprices->Insert( $insert );
			}
			else
			{
				//Line 0 is "Pacific ..."
				//Line 1 is a column header row which has commas"
				//Line 2 -> contains data OR the "We regret, "
				if( $linecount > 0 AND $linecount < 5 )
				{
					echo "No data in $filename";
					EmailAlert( "kevin", "FX Currencies Fail " . $value['currency'] . "-" . $value['foreigncurrency'], $filename . " apparantly doesn't contain any data" );
				}
			}
			$linecount++;
		}
	}
$fxprices->querystring = "delete from fxprices where day_close = '0' and day_high = '0'";
$fxprices->GenericQuery();
}

?>

<?php

require_once( 'common/webpage2txt.php' );
require_once( 'common/parse_line.php' );
require_once( 'common/ResultsToInsert.php' );
require_once( 'common/queryyahoo.php' );

echo __FILE__ . "\n";
require_once( '../local.php' );
require_once( 'data/generictable.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
include( $MODELDIR . '/stockinfo.class.php' );
$stock = new stockinfo();
include( $MODELDIR . '/stockexchange.class.php' );
$stockexchange = new stockexchange();
//include( 'view/class.genericpage.php' );
$stock->nolimit = TRUE;
$stock->limit = 10000;
$stock->where = "active <> '0'";
$stock->Select();
$stockexchange->Select();
	foreach( $stockexchange->resultarray as $key => $evalue )
	{
		$thisex[ $evalue['idstockexchange'] ] = $evalue['YahooSymbol'];
	}
	//var_dump( $thisex );
foreach( $stock->resultarray as $key => $value )
{
	$symbol = $value['stocksymbol'];
	if ( $symbol != 'CASH' )
	{
		$result = QueryYahoo( $symbol, $thisex[ $value['stockexchange'] ] );
//20100824 KF Added if result != NULL since I changed queryyahoo to return NULL when nothing in the CSV
		if( $result != NULL )
		{
			$insert = ResultsToInsert( $value, $result );
			$insert['reviseduser'] = "queryyahoo2";
			$insert['idstockinfo'] = $value['idstockinfo'];
			$stock->fieldspec[$symbol]['prikey'] = 'Y';
			echo "Saving data for stock " . $symbol . "\n";
			$stock->Update( $insert );  //20120624 using update because each of these stocks already exists in the table, 1 entry each
		}
//20100824 !NULL
		else
		{
			$fp = fopen( 'queryyahoo2_error.txt', 'w' );
			fwrite( $fp, "QueryYahoo returned NULL result for " . $symbol . " at " . date( DATE_RSS ) . "\n" );
			fclose( $fp );
		}
	}
}
?>

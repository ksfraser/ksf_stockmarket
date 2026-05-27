<?php

global $MODELDIR;
require_once( 'data/generictable.php' );
include_once( $MODELDIR . '/stockexchange.class.php' );

function yahooexchanges()
{
	$stockexchange = new stockexchange();
        $stockexchange->Select();
        foreach( $stockexchange->resultarray as $key => $evalue )
        {
                $thisex[ $evalue['idstockexchange'] ] = $evalue['YahooSymbol'];
        }
        //var_dump( $thisex );
	unset( $stockexchange );
	return $thisex;
}

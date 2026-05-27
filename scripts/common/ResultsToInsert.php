<?php

function ResultsToInsert( $stock, $results )
{
        $return['stocksymbol'] = $stock['stocksymbol'];
        $return['averagevolume'] = $results['average volume'] ;
        $return['low'] = $results['low'] ;
        $return['asofdate'] = date( 'Y-m-d', strtotime($results['trade date']) ) ;
        $return['high'] = $results['high'] ;
        $return['currentprice'] = $results['last trade'] ;
        $return['dailyvolume'] = $results['volume'];
        if ($results['high'] > $stock['yearhigh'])
                $return['yearhigh'] = $results['high'];
        if ($results['low'] < $stock['yearlow'])
                $return['yearlow'] = $results['low'];
        return $return;
}

?>

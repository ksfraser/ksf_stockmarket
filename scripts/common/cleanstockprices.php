<?php

require_once( 'data/generictable.php' );
require_once( $MODELDIR . '/stockprices.class.php' );


function cleanstockprices()
{
        $stockprices = new stockprices();
        $stockprices->querystring = "delete from stockprices where day_close = '0' and day_high = '0'";
        $stockprices->GenericQuery();
        $stockprices->querystring = "delete from stockprices where symbol = ' '";
        $stockprices->GenericQuery();
        unset( $stockprices );
        return SUCCESS;
}

?>

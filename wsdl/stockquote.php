<?php

include "SCA/SCA.php";

/**
 * Scaffold implementation for a remote StockQuote Web service.
 *
 * @service
 * @binding.soap
 *
 */
class stockquote {

    /**
     * Get a stock quote for a given ticker symbol.
     *
     * @param string $ticker The ticker symbol.
     * @return float The stock quote.
     */
    function getQuote($ticker) {
        return 80.9;
  }
}
?>


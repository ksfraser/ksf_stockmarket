<?php
   /**
     * The currency exchange rate service to use.
     *
     * @reference
     * @binding.php ExchangeRate.php
     */
    public $exchange_rate_proxy;

	//Example #1 Obtaining a proxy using getService - either a script-file or a wsdl
$exchange_rate = SCA::getService('ExchangeRate.php');
$stock_quote   = SCA::getService('StockQuote.wsdl');

//Methods on services can then be called on the returned proxy, just as they can in a component.
//Example #2 Making calls on the proxy

$quote  = $stock_quote->getQuote($ticker);
$rate   = $exchange_rate->getRate($currency);

?>





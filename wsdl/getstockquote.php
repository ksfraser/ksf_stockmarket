<?php
$wsdl = file_get_contents('http://defiant/finance/wsdl/stockquote.php?wsdl');
file_put_contents("service.wsdl",$wsdl); //write the wsdl to a file
$service = SCA::getService('service.wsdl'); 
$ret = $service->getQuote( "BOO" );
echo $ret
?>

<?php

// bind SOAP/Client.php -> path of the php file
require_once "SOAP/Client.php";

// URI delivered to web service
$sc = new SOAP_Client("http://defiant/finance/wsdl/SOAP.server.example.php");

// start call function to use the function of the Web Service
$parameter = array();
$result = $sc->call ("now", &$parameter, "urn:TimeSerivce");

// print result
print $result."\n";

?>

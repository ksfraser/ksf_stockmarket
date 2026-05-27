<?php

// bind PEAR::SOAP
require_once "SOAP/Server.php";
$skiptrace =& PEAR::getStaticProperty('PEAR_Error', 'skiptrace');
$skiptrace = true;

// program service class
class TimeSerivce {
    public function now () {
       
        date_default_timezone_set("America/Edmonton");
        return (date ("H:i:s"));
    }
}

// web service classs develop
$service = new TimeSerivce();

// server develop
$ss = new SOAP_SERVER();

// assing the name to the service
$ss->addObjectMap($service, "urn:TimeSerivce");

// service or wsdl
if (isset($_SERVER["REQUEST_METHOD"])&& $_SERVER["REQUEST_METHOD"] == "POST") {

    // postdata -> service
    $ss->service ($HTTP_RAW_POST_DATA);
   
} else {

  // wsdl-param in url
  if (isset($_SERVER['QUERY_STRING']) && strcasecmp($_SERVER['QUERY_STRING'],'wsdl') == 0) {
   
    // DISCO_Server for WSDL
    require_once "SOAP/Disco.php";
    $disco = new SOAP_DISCO_Server ($ss,"TimeService","My Time Service");
   
    // set HTML-Header
    header("Content-type: text/xml");
   
    // return wsdl
    print $disco->getWSDL ();
  }
} 


?>


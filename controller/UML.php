<?php
require_once 'PHP/UML.php';

$uml = new PHP_UML();   
$uml->parseFile('controller.php'); 
$uml->generateXMI(1);             // UML version number (1 or 2)
$uml->saveXMI('test.xmi');
?> 

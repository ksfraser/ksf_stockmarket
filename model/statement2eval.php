<?php

//copies the recent data out of fin_statement
//into evalmarket.

require_once( 'include_all.php' );

$days = 30; 	//number of days to insert for
		//designed for once a month

$query = "INSERT INTO evalmarket (  
  `idstockinfo`,
  `netincome`,
  `depreciation`,
  `depletion`,
  `amortization`,
  `capitalexpenses`,
  `workingcapital`,
  `outstandingshares`,
  `growthrate`,
  `ownerearnings`
)
  SELECT s.`idstockinfo`,
  s.`netincome`,
  s.`depreciation`,
  s.`depletion`,
  s.`amortization`,
  s.`capitalexpenses`,
  s.`workingcapital`,
  s.`outstandingshares`,
  s.`incomegrowth`,
  s.`ownerearnings`

  FROM fin_statement s
  WHERE s.lasteval > (CURDATE() - $days)";

require_once( 'evalmarket.class.php' );
$m = new evalmarket();
$m->querystring = $query;
$m->GenericQuery();

?>

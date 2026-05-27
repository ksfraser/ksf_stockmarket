<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('stock90highlow');
$form->addElement('text', 'stocksymbol', 'stocksymbol: Stock Symbol', array( 'size' => 10));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'high', 'high: ', array( 'size' => 32));
$form->addRule( 'high', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'low', 'low: ', array( 'size' => 32));
$form->addRule( 'low', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'currentprice', 'currentprice: ', array( 'size' => 32));
$form->addRule( 'currentprice', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: ', array( 'size' => 10));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createddate', 'createddate: ', array( 'size' => 32));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'reviseddate', 'reviseddate: ', array( 'size' => 32));
$form->addRule( 'reviseddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'active', 'active: Is this symbol still active', array( 'size' => 11));
$form->addRule( 'active', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'cik', 'cik: SEC's CIK value for the company', array( 'size' => 11));
$form->addRule( 'cik', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'KEY', 'KEY: ', array( 'size' => 32));

$form->setDefaults( array(
	'stocksymbol' => '',
	'high' => '',
	'low' => '',
	'currentprice' => '',
	'idstockinfo' => '',
	'createddate' => '',
	'reviseddate' => '',
	'active' => '',
	'cik' => '',
	'KEY' => '',
	)
);

$form->addElement('submit', null, 'Submit');

	if ( $form->validate() )
	{
		$form->freeze();
		//Now do something with the data
		require_once( 'data/generictable.php' );
		require_once( '../local.php' );
		Local_Init();
		include_once( '../model/stock90highlow.class.php' );
		$stock90highlow = new stock90highlow();
		$stock90highlow->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
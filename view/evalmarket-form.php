<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('evalmarket');
$form->addElement('text', 'netvalue', 'netvalue: The Assets - Liabilities from the financial Statement', array( 'size' => 11));
$form->addRule( 'netvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: Company', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'discountrate', 'discountrate: Discount Rate (Risk Free Rate - 30Yr bond + 3%)', array( 'size' => 11));
$form->addRule( 'discountrate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'incomegrowth', 'incomegrowth: year over year growth percentage', array( 'size' => 11));
$form->addRule( 'incomegrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'netincome', 'netincome: Net Income', array( 'size' => 10));
$form->addRule( 'netincome', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'depreciation', 'depreciation: Depreciation', array( 'size' => 10));
$form->addRule( 'depreciation', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'depletion', 'depletion: Depletion', array( 'size' => 10));
$form->addRule( 'depletion', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'amortization', 'amortization: Amortization', array( 'size' => 10));
$form->addRule( 'amortization', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'capitalexpenses', 'capitalexpenses: Capital Expense', array( 'size' => 10));
$form->addRule( 'capitalexpenses', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'workingcapital', 'workingcapital: Working Capital', array( 'size' => 10));
$form->addRule( 'workingcapital', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'user', 'user: Evaluating User', array( 'size' => 45));
$form->addRule( 'user', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'user', 'ERROR: Missing value', 'required');

$form->addElement('text', 'outstandingshares', 'outstandingshares: Number of Outstanding Shares', array( 'size' => 10));
$form->addRule( 'outstandingshares', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'netvalue' => '0',
	'idstockinfo' => '',
	'discountrate' => '10',
	'incomegrowth' => '',
	'netincome' => '',
	'depreciation' => '',
	'depletion' => '',
	'amortization' => '',
	'capitalexpenses' => '',
	'workingcapital' => '',
	'user' => '',
	'outstandingshares' => '',
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
		include_once( '../model/evalmarket.class.php' );
		$evalmarket = new evalmarket();
		$evalmarket->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
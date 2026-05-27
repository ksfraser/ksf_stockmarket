<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('quarter_statement');
$form->addElement('text', 'idstockinfo', 'idstockinfo: ', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'netincome', 'netincome: ', array( 'size' => 11));
$form->addRule( 'netincome', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'depletion', 'depletion: ', array( 'size' => 11));
$form->addRule( 'depletion', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'amortization', 'amortization: ', array( 'size' => 11));
$form->addRule( 'amortization', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'capitalexpenses', 'capitalexpenses: ', array( 'size' => 11));
$form->addRule( 'capitalexpenses', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'workingcapital', 'workingcapital: ', array( 'size' => 11));
$form->addRule( 'workingcapital', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'lasteval', 'lasteval: ', array( 'size' => 11));
$form->addRule( 'lasteval', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'user', 'user: ', array( 'size' => 11));
$form->addRule( 'user', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'outstandingshares', 'outstandingshares: ', array( 'size' => 11));
$form->addRule( 'outstandingshares', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'incomegrowth', 'incomegrowth: Year over year Income Growth %', array( 'size' => 11));
$form->addRule( 'incomegrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'ownerearnings', 'ownerearnings: ', array( 'size' => 11));
$form->addRule( 'ownerearnings', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totalasset', 'totalasset: ', array( 'size' => 11));
$form->addRule( 'totalasset', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totalliability', 'totalliability: ', array( 'size' => 11));
$form->addRule( 'totalliability', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totalequity', 'totalequity: ', array( 'size' => 11));
$form->addRule( 'totalequity', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totaldebt', 'totaldebt: ', array( 'size' => 11));
$form->addRule( 'totaldebt', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendpershare', 'dividendpershare: ', array( 'size' => 11));
$form->addRule( 'dividendpershare', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'earningpershare', 'earningpershare: Annual Earnings per share', array( 'size' => 11));
$form->addRule( 'earningpershare', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenue', 'revenue: Revenue from Income Statement', array( 'size' => 11));
$form->addRule( 'revenue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'retainedearnings', 'retainedearnings: Retained Earnings', array( 'size' => 11));
$form->addRule( 'retainedearnings', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenuegrowth', 'revenuegrowth: Growth in revenue compared to previous year', array( 'size' => 11));
$form->addRule( 'revenuegrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenuegrowth2', 'revenuegrowth2: Revenue Growth compared to 2 years ago', array( 'size' => 11));
$form->addRule( 'revenuegrowth2', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenuegrowth3', 'revenuegrowth3: Revenue Growth compared to 3 years ago', array( 'size' => 11));
$form->addRule( 'revenuegrowth3', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'idstockinfo' => '',
	'netincome' => '',
	'depletion' => '',
	'amortization' => '',
	'capitalexpenses' => '',
	'workingcapital' => '',
	'lasteval' => '',
	'user' => '',
	'outstandingshares' => '',
	'incomegrowth' => '',
	'ownerearnings' => '',
	'totalasset' => '',
	'totalliability' => '',
	'totalequity' => '',
	'totaldebt' => '',
	'dividendpershare' => '',
	'earningpershare' => '',
	'revenue' => '',
	'retainedearnings' => '',
	'revenuegrowth' => '',
	'revenuegrowth2' => '',
	'revenuegrowth3' => '',
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
		include_once( '../model/quarter_statement.class.php' );
		$quarter_statement = new quarter_statement();
		$quarter_statement->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
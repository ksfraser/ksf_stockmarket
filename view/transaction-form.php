<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('transaction');
$form->addElement('text', 'idusers', 'idusers: User', array( 'size' => 11));
$form->addRule( 'idusers', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'account', 'account: Which account is this transaction in (TRADE/RRSP/TFSA) ', array( 'size' => 11));
$form->addRule( 'account', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'currency', 'currency: Home Currency', array( 'size' => 11));
$form->addRule( 'currency', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'foreigncurrency', 'foreigncurrency: Foreign Currency', array( 'size' => 11));
$form->addRule( 'foreigncurrency', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'transactiondate', 'transactiondate: Transaction Date', array( 'size' => 10));
$form->addRule( 'transactiondate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'username', 'username: User', array( 'size' => 45));
$form->addRule( 'username', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'username', 'ERROR: Missing value', 'required');

$form->addElement('text', 'stocksymbol', 'stocksymbol: Stock', array( 'size' => 45));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'stocksymbol', 'ERROR: Missing value', 'required');

$form->addElement('text', 'numbershares', 'numbershares: Number', array( 'size' => 11));
$form->addRule( 'numbershares', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'numbershares', 'ERROR: Missing value', 'required');

$form->addElement('text', 'transactiontype', 'transactiontype: Transaction Type', array( 'size' => 45));
$form->addRule( 'transactiontype', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'transactiontype', 'ERROR: Missing value', 'required');

$form->addElement('text', 'dollar', 'dollar: Dollars', array( 'size' => 45));
$form->addRule( 'dollar', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'dollar', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'idusers' => '',
	'account' => 'TRADE',
	'currency' => 'CAD',
	'foreigncurrency' => 'CAD',
	'transactiondate' => '',
	'username' => '',
	'stocksymbol' => '',
	'numbershares' => '0',
	'transactiontype' => '',
	'dollar' => '',
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
		include_once( '../model/transaction.class.php' );
		$transaction = new transaction();
		$transaction->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
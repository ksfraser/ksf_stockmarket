<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('transaction_close');
$form->addElement('text', 'username', 'username: ', array( 'size' => 11));
$form->addRule( 'username', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'transactiondate', 'transactiondate: Transaction Date', array( 'size' => 11));
$form->addRule( 'transactiondate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: stockinfo index', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'stocksymbol', 'stocksymbol: ', array( 'size' => 11));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'numbershares', 'numbershares: ', array( 'size' => 11));
$form->addRule( 'numbershares', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'transactiontype', 'transactiontype: ', array( 'size' => 11));
$form->addRule( 'transactiontype', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'dollar', 'dollar: ', array( 'size' => 11));
$form->addRule( 'dollar', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idusers', 'idusers: User', array( 'size' => 11));
$form->addRule( 'idusers', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'account', 'account: Which account is this transaction in (TRADE/RRSP/TFSA) ', array( 'size' => 11));
$form->addRule( 'account', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'currency', 'currency: Home Currency', array( 'size' => 11));
$form->addRule( 'currency', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createduser', 'createduser: ', array( 'size' => 11));
$form->addRule( 'createduser', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createddate', 'createddate: ', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'reviseddate', 'reviseddate: ', array( 'size' => 11));
$form->addRule( 'reviseddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'reviseduser', 'reviseduser: ', array( 'size' => 11));
$form->addRule( 'reviseduser', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'closeBreakEven', 'closeBreakEven: Break Even close', array( 'size' => 11));
$form->addRule( 'closeBreakEven', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'closeLong', 'closeLong: Close Long', array( 'size' => 11));
$form->addRule( 'closeLong', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'closeShort', 'closeShort: Close Short', array( 'size' => 11));
$form->addRule( 'closeShort', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'closeTimeLimit', 'closeTimeLimit: Close after so many days', array( 'size' => 11));
$form->addRule( 'closeTimeLimit', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'closePartial', 'closePartial: Target for closing part of the position', array( 'size' => 11));
$form->addRule( 'closePartial', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'closeTargetPrice', 'closeTargetPrice: Close once a target price is met', array( 'size' => 11));
$form->addRule( 'closeTargetPrice', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'closeValueAtRisk', 'closeValueAtRisk: Close once a Value At Risk is hit', array( 'size' => 11));
$form->addRule( 'closeValueAtRisk', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'stopsize', 'stopsize: The Stop Size diff between high price and stop price', array( 'size' => 11));
$form->addRule( 'stopsize', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'turtle_long_close', 'turtle_long_close: Turtle Strategy initial Long close price', array( 'size' => 11));
$form->addRule( 'turtle_long_close', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'turtle_short_close', 'turtle_short_close: Turtle Strategy initial Short close price', array( 'size' => 11));
$form->addRule( 'turtle_short_close', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'CONSTRAINT', 'CONSTRAINT: ', array( 'size' => 11));

$form->setDefaults( array(
	'username' => '',
	'transactiondate' => '',
	'idstockinfo' => '',
	'stocksymbol' => '',
	'numbershares' => '',
	'transactiontype' => '',
	'dollar' => '',
	'idusers' => '',
	'account' => '',
	'currency' => '',
	'createduser' => '',
	'createddate' => '',
	'reviseddate' => '',
	'reviseduser' => '',
	'closeBreakEven' => '',
	'closeLong' => '',
	'closeShort' => '',
	'closeTimeLimit' => '',
	'closePartial' => '',
	'closeTargetPrice' => '',
	'closeValueAtRisk' => '',
	'stopsize' => '',
	'turtle_long_close' => '',
	'turtle_short_close' => '',
	'CONSTRAINT' => '',
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
		include_once( '../model/transaction_close.class.php' );
		$transaction_close = new transaction_close();
		$transaction_close->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
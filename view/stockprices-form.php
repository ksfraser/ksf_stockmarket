<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('stockprices');
$form->addElement('text', 'adjustedclose', 'adjustedclose: Split Adjusted Close Price', array( 'size' => 11));
$form->addRule( 'adjustedclose', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'symbol', 'symbol: ', array( 'size' => 11));
$form->addRule( 'symbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'date', 'date: ', array( 'size' => 11));
$form->addRule( 'date', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'previous_close', 'previous_close: ', array( 'size' => 11));
$form->addRule( 'previous_close', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_open', 'day_open: ', array( 'size' => 11));
$form->addRule( 'day_open', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_low', 'day_low: ', array( 'size' => 11));
$form->addRule( 'day_low', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_high', 'day_high: ', array( 'size' => 11));
$form->addRule( 'day_high', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_close', 'day_close: ', array( 'size' => 11));
$form->addRule( 'day_close', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_change', 'day_change: ', array( 'size' => 11));
$form->addRule( 'day_change', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bid', 'bid: ', array( 'size' => 11));
$form->addRule( 'bid', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'ask', 'ask: ', array( 'size' => 11));
$form->addRule( 'ask', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'volume', 'volume: ', array( 'size' => 11));
$form->addRule( 'volume', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'adjustedclose' => '',
	'symbol' => '',
	'date' => '',
	'previous_close' => '',
	'day_open' => '',
	'day_low' => '',
	'day_high' => '',
	'day_close' => '',
	'day_change' => '',
	'bid' => '',
	'ask' => '',
	'volume' => '',
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
		include_once( '../model/stockprices.class.php' );
		$stockprices = new stockprices();
		$stockprices->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
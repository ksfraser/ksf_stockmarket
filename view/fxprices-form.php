<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('fxprices');
$form->addElement('text', 'currency', 'currency: ', array( 'size' => 11));
$form->addRule( 'currency', 'ERROR: Incorrect data type', 'alphanumeric');

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

$form->addElement('text', 'foreigncurrency', 'foreigncurrency: Foreign Currency', array( 'size' => 11));
$form->addRule( 'foreigncurrency', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'foreigncurrency', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'currency' => '',
	'date' => '',
	'previous_close' => '',
	'day_open' => '',
	'day_low' => '',
	'day_high' => '',
	'day_close' => '',
	'day_change' => '',
	'foreigncurrency' => '0',
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
		include_once( '../model/fxprices.class.php' );
		$fxprices = new fxprices();
		$fxprices->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
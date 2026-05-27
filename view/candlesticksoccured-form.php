<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('candlesticksoccured');
$form->addElement('text', 'createddate', 'createddate: Record Created Date', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createduser', 'createduser: Record Created by User', array( 'size' => 11));
$form->addRule( 'createduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateddate', 'updateddate: Record updated date', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateduser', 'updateduser: Record Updated by user', array( 'size' => 11));
$form->addRule( 'updateduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'symbol', 'symbol: Stock Symbol', array( 'size' => 11));
$form->addRule( 'symbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'date', 'date: Date in stockprices', array( 'size' => 11));
$form->addRule( 'date', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'candlestick', 'candlestick: Candlestick Identified for this date', array( 'size' => 255));
$form->addRule( 'candlestick', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'createddate' => '',
	'createduser' => '',
	'updateddate' => '',
	'updateduser' => '',
	'symbol' => '',
	'date' => '',
	'candlestick' => '',
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
		include_once( '../model/candlesticksoccured.class.php' );
		$candlesticksoccured = new candlesticksoccured();
		$candlesticksoccured->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
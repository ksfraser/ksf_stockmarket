<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('candlestickactions');
$form->addElement('text', 'candlestick_name', 'candlestick_name: The name of the candlestick', array( 'size' => 32));
$form->addRule( 'candlestick_name', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'candlestick_name11', 'candlestick_name11: The name trimmed to 11 chars as that happened in some tables', array( 'size' => 11));
$form->addRule( 'candlestick_name11', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'candlestick_detail', 'candlestick_detail: Details on the meaning of the candlestick', array( 'size' => 255));
$form->addRule( 'candlestick_detail', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'candlestick_action', 'candlestick_action: What action to take because of this candlestick', array( 'size' => 32));
$form->addRule( 'candlestick_action', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'candlestick_action_value', 'candlestick_action_value: Action Strength value', array( 'size' => 11));
$form->addRule( 'candlestick_action_value', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'candlestick_name' => '',
	'candlestick_name11' => '',
	'candlestick_detail' => '',
	'candlestick_action' => '',
	'candlestick_action_value' => '50',
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
		include_once( '../model/candlestickactions.class.php' );
		$candlestickactions = new candlestickactions();
		$candlestickactions->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
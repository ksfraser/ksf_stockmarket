<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('heikanashi');
$form->addElement('text', 'day_open', 'day_open: The Heiken Ashi Day Open value', array( 'size' => 11));
$form->addRule( 'day_open', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_close', 'day_close: The Heiken Ashi Day Close value', array( 'size' => 11));
$form->addRule( 'day_close', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_high', 'day_high: The Heiken Ashi Day High value', array( 'size' => 11));
$form->addRule( 'day_high', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'day_low', 'day_low: The Heiken Ashi Day Low value', array( 'size' => 11));
$form->addRule( 'day_low', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'day_open' => '',
	'day_close' => '',
	'day_high' => '',
	'day_low' => '',
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
		include_once( '../model/heikanashi.class.php' );
		$heikanashi = new heikanashi();
		$heikanashi->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
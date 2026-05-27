<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('cash');
$form->addElement('text', 'name', 'name: ', array( 'size' => 11));
$form->addRule( 'name', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'value', 'value: ', array( 'size' => 11));
$form->addRule( 'value', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'currency', 'currency: ', array( 'size' => 11));
$form->addRule( 'currency', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'type', 'type: ', array( 'size' => 11));
$form->addRule( 'type', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'owner', 'owner: ', array( 'size' => 11));
$form->addRule( 'owner', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'cost', 'cost: ', array( 'size' => 11));
$form->addRule( 'cost', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'date', 'date: ', array( 'size' => 11));
$form->addRule( 'date', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'name' => '',
	'value' => '',
	'currency' => '',
	'type' => '',
	'owner' => '',
	'cost' => '',
	'date' => '',
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
		include_once( '../model/cash.class.php' );
		$cash = new cash();
		$cash->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('alerts');
$form->addElement('text', 'alertdescription', 'alertdescription: Description', array( 'size' => 45));
$form->addRule( 'alertdescription', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'alertdescription', 'ERROR: Missing value', 'required');

$form->addElement('text', 'alertfunctionname', 'alertfunctionname: Called Function', array( 'size' => 45));
$form->addRule( 'alertfunctionname', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'alertfunctionname', 'ERROR: Missing value', 'required');

$form->addElement('text', 'expirydate', 'expirydate: Expiry Date of Alert', array( 'size' => 11));
$form->addRule( 'expirydate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'alertdescription' => '',
	'alertfunctionname' => '',
	'expirydate' => '',
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
		include_once( '../model/alerts.class.php' );
		$alerts = new alerts();
		$alerts->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
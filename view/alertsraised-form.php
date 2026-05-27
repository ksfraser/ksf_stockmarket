<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('alertsraised');
$form->addElement('text', 'idalertsraised', 'idalertsraised: Index', array( 'size' => 10));
$form->addRule( 'idalertsraised', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'idalertsraised', 'ERROR: Missing value', 'required');

$form->addElement('text', 'cleared', 'cleared: Cleared Flag', array( 'size' => 11));
$form->addRule( 'cleared', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'raisedtimestamp', 'raisedtimestamp: Alert Raised', array( 'size' => 17));
$form->addRule( 'raisedtimestamp', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'raisedtimestamp', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'idalertsraised' => '',
	'cleared' => '0',
	'raisedtimestamp' => 'CURRENT_TIMESTAMP',
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
		include_once( '../model/alertsraised.class.php' );
		$alertsraised = new alertsraised();
		$alertsraised->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
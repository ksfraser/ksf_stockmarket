<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('scriptlog');
$form->addElement('text', 'date', 'date: ', array( 'size' => 11));
$form->addRule( 'date', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'scriptname', 'scriptname: ', array( 'size' => 11));
$form->addRule( 'scriptname', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'scriptstep', 'scriptstep: ', array( 'size' => 11));
$form->addRule( 'scriptstep', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'date' => '',
	'scriptname' => '',
	'scriptstep' => '',
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
		include_once( '../model/scriptlog.class.php' );
		$scriptlog = new scriptlog();
		$scriptlog->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('bondrate');
$form->addElement('text', 'calendaryear', 'calendaryear: Calendar Year', array( 'size' => 19));
$form->addRule( 'calendaryear', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'calendaryear', 'ERROR: Missing value', 'required');

$form->addElement('text', 'bondrate', 'bondrate: Bond Rate', array( 'size' => 11));
$form->addRule( 'bondrate', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'bondrate', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'calendaryear' => '',
	'bondrate' => '3',
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
		include_once( '../model/bondrate.class.php' );
		$bondrate = new bondrate();
		$bondrate->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
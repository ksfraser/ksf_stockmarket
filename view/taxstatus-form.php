<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('taxstatus');
$form->addElement('text', 'idtaxstatus', 'idtaxstatus: Index', array( 'size' => 11));
$form->addRule( 'idtaxstatus', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'taxstatus', 'taxstatus: Tax Status', array( 'size' => 11));
$form->addRule( 'taxstatus', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'notes', 'notes: Notes', array( 'size' => 11));
$form->addRule( 'notes', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createduser', 'createduser: Created By User', array( 'size' => 11));

$form->addElement('text', 'createddate', 'createddate: Created Date', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'updateduser', 'updateduser: Updated by User', array( 'size' => 11));
$form->addRule( 'updateduser', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'updateddate', 'updateddate: Updated by User', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'idtaxstatus' => '',
	'taxstatus' => '',
	'notes' => '',
	'createduser' => '',
	'createddate' => '',
	'updateduser' => '',
	'updateddate' => '',
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
		include_once( '../model/taxstatus.class.php' );
		$taxstatus = new taxstatus();
		$taxstatus->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
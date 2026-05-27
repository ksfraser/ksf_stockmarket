<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('stockalert');
$form->addElement('text', 'idalerts', 'idalerts: Alert', array( 'size' => 11));
$form->addRule( 'idalerts', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'idalerts', 'ERROR: Missing value', 'required');

$form->addElement('text', 'idstockinfo', 'idstockinfo: Stock Symbol', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'idstockinfo', 'ERROR: Missing value', 'required');

$form->addElement('text', 'username', 'username: User', array( 'size' => 45));
$form->addRule( 'username', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'username', 'ERROR: Missing value', 'required');

$form->addElement('text', 'value1', 'value1: First Criteria', array( 'size' => 45));
$form->addRule( 'value1', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'value1', 'ERROR: Missing value', 'required');

$form->addElement('text', 'value2', 'value2: Second Criteria', array( 'size' => 45));
$form->addRule( 'value2', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'value2', 'ERROR: Missing value', 'required');

$form->addElement('text', 'runonce', 'runonce: Run Once', array( 'size' => 11));
$form->addRule( 'runonce', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'runstatus', 'runstatus: Run Status', array( 'size' => 11));
$form->addRule( 'runstatus', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'idalerts' => '',
	'idstockinfo' => '',
	'username' => '',
	'value1' => '',
	'value2' => '',
	'runonce' => '0',
	'runstatus' => '0',
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
		include_once( '../model/stockalert.class.php' );
		$stockalert = new stockalert();
		$stockalert->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
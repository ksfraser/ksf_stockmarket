<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('transactiontype');
$form->addElement('text', 'AddSub', 'AddSub: Add or Subtract transaction', array( 'size' => 11));
$form->addRule( 'AddSub', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'transactiontype', 'transactiontype: Transaction Type', array( 'size' => 45));
$form->addRule( 'transactiontype', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'transactiontype', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'AddSub' => '1',
	'transactiontype' => '',
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
		include_once( '../model/transactiontype.class.php' );
		$transactiontype = new transactiontype();
		$transactiontype->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
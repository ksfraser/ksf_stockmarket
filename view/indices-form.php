<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('indices');
$form->addElement('text', 'symbol', 'symbol: ', array( 'size' => 11));
$form->addRule( 'symbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'stockindex', 'stockindex: ', array( 'size' => 11));
$form->addRule( 'stockindex', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'symbol' => '',
	'stockindex' => '',
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
		include_once( '../model/indices.class.php' );
		$indices = new indices();
		$indices->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
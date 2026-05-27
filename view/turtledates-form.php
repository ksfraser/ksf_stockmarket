<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('turtledates');
$form->setDefaults( array(
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
		include_once( '../model/turtledates.class.php' );
		$turtledates = new turtledates();
		$turtledates->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
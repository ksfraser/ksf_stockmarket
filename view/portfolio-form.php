<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('portfolio');
$form->addElement('text', 'account', 'account: Account', array( 'size' => 45));
$form->addRule( 'account', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'account', 'ERROR: Missing value', 'required');

$form->addElement('text', 'bookvalue', 'bookvalue: Book Value', array( 'size' => 11));
$form->addRule( 'bookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marketvalue', 'marketvalue: Market Value', array( 'size' => 11));
$form->addRule( 'marketvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'currentprice', 'currentprice: Current Price', array( 'size' => 11));
$form->addRule( 'currentprice', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'account' => 'ALL',
	'bookvalue' => '0',
	'marketvalue' => '0',
	'currentprice' => '0',
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
		include_once( '../model/portfolio.class.php' );
		$portfolio = new portfolio();
		$portfolio->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
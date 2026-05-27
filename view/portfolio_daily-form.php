<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('portfolio_daily');
$form->addElement('text', 'username', 'username: The user', array( 'size' => 11));
$form->addRule( 'username', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'tradedate', 'tradedate: The date for this row of history', array( 'size' => 11));
$form->addRule( 'tradedate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'bookvalue', 'bookvalue: The book value of the portfolio on this date', array( 'size' => 11));
$form->addRule( 'bookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marketvalue', 'marketvalue: The market value of the portfolio on this date', array( 'size' => 11));
$form->addRule( 'marketvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'cash', 'cash: Cash in the portfolio on this date', array( 'size' => 11));
$form->addRule( 'cash', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateddate', 'updateddate: The date this record was last updated', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'account', 'account: The account this record is for', array( 'size' => 11));
$form->addRule( 'account', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'username' => '',
	'tradedate' => '',
	'bookvalue' => '',
	'marketvalue' => '',
	'cash' => '',
	'updateddate' => '',
	'account' => '',
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
		include_once( '../model/portfolio_daily.class.php' );
		$portfolio_daily = new portfolio_daily();
		$portfolio_daily->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
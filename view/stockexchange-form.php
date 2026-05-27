<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('stockexchange');
$form->addElement('text', 'exchange', 'exchange: Exchange Name', array( 'size' => 45));
$form->addRule( 'exchange', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'exchange', 'ERROR: Missing value', 'required');

$form->addElement('text', 'YahooSymbol', 'YahooSymbol: Yahoo Finance Symbol', array( 'size' => 45));
$form->addRule( 'YahooSymbol', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'YahooSymbol', 'ERROR: Missing value', 'required');

$form->addElement('text', 'GlobeInvestorSymbol', 'GlobeInvestorSymbol: Globe Investor Symbol', array( 'size' => 45));
$form->addRule( 'GlobeInvestorSymbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'exchange' => '',
	'YahooSymbol' => '',
	'GlobeInvestorSymbol' => '',
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
		include_once( '../model/stockexchange.class.php' );
		$stockexchange = new stockexchange();
		$stockexchange->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
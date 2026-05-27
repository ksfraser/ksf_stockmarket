<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('hedgefolios');
$form->addElement('text', 'idstockinfo', 'idstockinfo: The Stock being evaluated', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createddate', 'createddate: Time that this record was created', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createduser', 'createduser: Record created by user', array( 'size' => 11));
$form->addRule( 'createduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateddate', 'updateddate: The time this record was updated', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateduser', 'updateduser: Record updated by user', array( 'size' => 11));
$form->addRule( 'updateduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'supportlevel', 'supportlevel: The technical indicator Support Level', array( 'size' => 11));
$form->addRule( 'supportlevel', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'resistancelevel', 'resistancelevel: Technical indicator Resistance Level', array( 'size' => 11));
$form->addRule( 'resistancelevel', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'Volume', 'Volume: Average trading volume', array( 'size' => 11));
$form->addRule( 'Volume', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bollingerbands', 'bollingerbands: The Bollinger Bands levels', array( 'size' => 11));
$form->addRule( 'bollingerbands', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'elliotwave', 'elliotwave: The Elliot Wave values', array( 'size' => 11));
$form->addRule( 'elliotwave', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'fibonacci', 'fibonacci: Fibonacci indicators', array( 'size' => 11));
$form->addRule( 'fibonacci', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'sentiment', 'sentiment: Sentiment Indicators', array( 'size' => 11));
$form->addRule( 'sentiment', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'trailingpe', 'trailingpe: Trailing Price to Earnings', array( 'size' => 11));
$form->addRule( 'trailingpe', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'forwardpe', 'forwardpe: Forward Price to Earnings', array( 'size' => 11));
$form->addRule( 'forwardpe', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'pricetobook', 'pricetobook: Price to Book', array( 'size' => 11));
$form->addRule( 'pricetobook', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'pricetosale', 'pricetosale: Price to Sale', array( 'size' => 11));
$form->addRule( 'pricetosale', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'pricetocash', 'pricetocash: Price to Cash Flow', array( 'size' => 11));
$form->addRule( 'pricetocash', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'expectedgrowth', 'expectedgrowth: 5 years expected earnings growth', array( 'size' => 11));
$form->addRule( 'expectedgrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'chartpattern', 'chartpattern: Chart Patterns', array( 'size' => 11));
$form->addRule( 'chartpattern', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'candlesticks', 'candlesticks: Candlesticks', array( 'size' => 11));
$form->addRule( 'candlesticks', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'idstockinfo' => '',
	'createddate' => '',
	'createduser' => '',
	'updateddate' => '',
	'updateduser' => '',
	'supportlevel' => '',
	'resistancelevel' => '',
	'Volume' => '',
	'bollingerbands' => '',
	'elliotwave' => '',
	'fibonacci' => '',
	'sentiment' => '',
	'trailingpe' => '',
	'forwardpe' => '',
	'pricetobook' => '',
	'pricetosale' => '',
	'pricetocash' => '',
	'expectedgrowth' => '',
	'chartpattern' => '',
	'candlesticks' => '',
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
		include_once( '../model/hedgefolios.class.php' );
		$hedgefolios = new hedgefolios();
		$hedgefolios->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
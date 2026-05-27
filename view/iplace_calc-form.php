<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('iplace_calc');
$form->addElement('text', 'earningsgrowth', 'earningsgrowth: Are earnings growing', array( 'size' => 11));
$form->addRule( 'earningsgrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'earningsaccel', 'earningsaccel: Are earnings growth accelerating', array( 'size' => 11));
$form->addRule( 'earningsaccel', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'pe', 'pe: Price to Earnings ratio', array( 'size' => 11));
$form->addRule( 'pe', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'tradingvolume', 'tradingvolume: Trading Volume', array( 'size' => 11));
$form->addRule( 'tradingvolume', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'institutioninterest', 'institutioninterest: Percentage of shares owned by institutions', array( 'size' => 11));
$form->addRule( 'institutioninterest', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'orderimbalance', 'orderimbalance: Balance of buy and sell orders', array( 'size' => 11));
$form->addRule( 'orderimbalance', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'shortinterest', 'shortinterest: Is there a lot of short options sold', array( 'size' => 11));
$form->addRule( 'shortinterest', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'volatility', 'volatility: The volatility of the share', array( 'size' => 11));
$form->addRule( 'volatility', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createduser', 'createduser: Created By User', array( 'size' => 11));

$form->addElement('text', 'createddate', 'createddate: Created Date', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'updateduser', 'updateduser: Updated by User', array( 'size' => 11));

$form->addElement('text', 'updateddate', 'updateddate: Updated Date', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: Company', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendearningratio', 'dividendearningratio: Dividends per share divided by earnings per share', array( 'size' => 11));
$form->addRule( 'dividendearningratio', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'extracash', 'extracash: Does the company have cash on hand', array( 'size' => 11));
$form->addRule( 'extracash', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'shareholderprofitgoal', 'shareholderprofitgoal: Management focused on shareholder profit', array( 'size' => 11));
$form->addRule( 'shareholderprofitgoal', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendincreases', 'dividendincreases: Track record of dividend increases', array( 'size' => 11));
$form->addRule( 'dividendincreases', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'score', 'score: Score of this filter', array( 'size' => 11));
$form->addRule( 'score', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'earningsgrowth' => '',
	'earningsaccel' => '',
	'pe' => '',
	'tradingvolume' => '',
	'institutioninterest' => '',
	'orderimbalance' => '',
	'shortinterest' => '',
	'volatility' => '',
	'createduser' => '',
	'createddate' => '',
	'updateduser' => '',
	'updateddate' => '',
	'idstockinfo' => '',
	'dividendearningratio' => '',
	'extracash' => '',
	'shareholderprofitgoal' => '',
	'dividendincreases' => '',
	'score' => '',
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
		include_once( '../model/iplace_calc.class.php' );
		$iplace_calc = new iplace_calc();
		$iplace_calc->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
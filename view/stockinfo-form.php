<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('stockinfo');
$form->addElement('text', 'marketcap', 'marketcap: The Market Capitalization', array( 'size' => 11));
$form->addRule( 'marketcap', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'peratio', 'peratio: The PE Ratio', array( 'size' => 11));
$form->addRule( 'peratio', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'active', 'active: Is this symbol still active', array( 'size' => 11));
$form->addRule( 'active', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'cik', 'cik: CIK', array( 'size' => 11));
$form->addRule( 'cik', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'idstocksector', 'idstocksector: Stock Sector', array( 'size' => 11));

$form->addElement('text', 'createddate', 'createddate: ', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createduser', 'createduser: ', array( 'size' => 11));
$form->addRule( 'createduser', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'reviseddate', 'reviseddate: ', array( 'size' => 11));
$form->addRule( 'reviseddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'reviseduser', 'reviseduser: ', array( 'size' => 11));
$form->addRule( 'reviseduser', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'stocksymbol', 'stocksymbol: Stock Symbol', array( 'size' => 10));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'stocksymbol', 'ERROR: Missing value', 'required');

$form->addElement('text', 'corporatename', 'corporatename: Corporate Name', array( 'size' => 255));
$form->addRule( 'corporatename', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'currentprice', 'currentprice: Last Trade Price', array( 'size' => 11));
$form->addRule( 'currentprice', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('hidden', 'stockexchange', 'stockexchange: Stock Exchange', array( 'size' => 11));
$form->addRule( 'stockexchange', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'low', 'low: Low', array( 'size' => 11));
$form->addRule( 'low', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'low', 'ERROR: Missing value', 'required');

$form->addElement('text', 'high', 'high: High', array( 'size' => 11));
$form->addRule( 'high', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'high', 'ERROR: Missing value', 'required');

$form->addElement('text', 'yearlow', 'yearlow: 52 Week Low', array( 'size' => 11));
$form->addRule( 'yearlow', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'yearlow', 'ERROR: Missing value', 'required');

$form->addElement('text', 'yearhigh', 'yearhigh: 52 Week High', array( 'size' => 11));
$form->addRule( 'yearhigh', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'yearhigh', 'ERROR: Missing value', 'required');

$form->addElement('text', 'averagevolume', 'averagevolume: Average Volume', array( 'size' => 11));
$form->addRule( 'averagevolume', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dailyvolume', 'dailyvolume: Daily Trading Volume', array( 'size' => 11));
$form->addRule( 'dailyvolume', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'EPS', 'EPS: Earnings Per Share', array( 'size' => 11));
$form->addRule( 'EPS', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'annualdividendpershare', 'annualdividendpershare: Annual Dividend per Share', array( 'size' => 11));
$form->addRule( 'annualdividendpershare', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'asofdate', 'asofdate: Last Update Date', array( 'size' => 16));
$form->addRule( 'asofdate', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'marketcap' => '',
	'peratio' => '',
	'active' => '',
	'cik' => '',
	'idstocksector' => '',
	'createddate' => '',
	'createduser' => '',
	'reviseddate' => '',
	'reviseduser' => '',
	'stocksymbol' => '',
	'corporatename' => '',
	'currentprice' => '',
	'stockexchange' => '',
	'low' => '',
	'high' => '',
	'yearlow' => '99999',
	'yearhigh' => '',
	'averagevolume' => '',
	'dailyvolume' => '-1',
	'EPS' => '',
	'annualdividendpershare' => '0',
	'asofdate' => 'CURRENT_TIMESTAMP',
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
		include_once( '../model/stockinfo.class.php' );
		$stockinfo = new stockinfo();
		$stockinfo->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
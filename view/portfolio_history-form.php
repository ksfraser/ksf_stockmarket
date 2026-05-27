<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('portfolio_history');
$form->addElement('text', 'stocksymbol', 'stocksymbol: ', array( 'size' => 10));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'username', 'username: ', array( 'size' => 45));
$form->addRule( 'username', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'numbershares', 'numbershares: ', array( 'size' => 10));
$form->addRule( 'numbershares', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bookvalue', 'bookvalue: ', array( 'size' => 10));
$form->addRule( 'bookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marketvalue', 'marketvalue: ', array( 'size' => 10));
$form->addRule( 'marketvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'currentprice', 'currentprice: ', array( 'size' => 10));
$form->addRule( 'currentprice', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'profitloss', 'profitloss: ', array( 'size' => 10));
$form->addRule( 'profitloss', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marketbook', 'marketbook: ', array( 'size' => 10));
$form->addRule( 'marketbook', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'annualdividendpershare', 'annualdividendpershare: ', array( 'size' => 10));
$form->addRule( 'annualdividendpershare', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendpercentbookvalue', 'dividendpercentbookvalue: ', array( 'size' => 10));
$form->addRule( 'dividendpercentbookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendpercentmarketvalue', 'dividendpercentmarketvalue: ', array( 'size' => 10));
$form->addRule( 'dividendpercentmarketvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'lastupdate', 'lastupdate: ', array( 'size' => 17));
$form->addRule( 'lastupdate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendyield', 'dividendyield: ', array( 'size' => 10));
$form->addRule( 'dividendyield', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'percenttotalbookvalue', 'percenttotalbookvalue: ', array( 'size' => 10));
$form->addRule( 'percenttotalbookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'percenttotalmarketvalue', 'percenttotalmarketvalue: ', array( 'size' => 10));
$form->addRule( 'percenttotalmarketvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'percenttotaldividend', 'percenttotaldividend: ', array( 'size' => 10));
$form->addRule( 'percenttotaldividend', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idportfolio_history', 'idportfolio_history: ', array( 'size' => 10));
$form->addRule( 'idportfolio_history', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'yield', 'yield: ', array( 'size' => 10));
$form->addRule( 'yield', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'annualdividend', 'annualdividend: ', array( 'size' => 10));
$form->addRule( 'annualdividend', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendbookvalue', 'dividendbookvalue: ', array( 'size' => 10));
$form->addRule( 'dividendbookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'stocksymbol' => '',
	'username' => '',
	'numbershares' => '',
	'bookvalue' => '',
	'marketvalue' => '',
	'currentprice' => '',
	'profitloss' => '',
	'marketbook' => '',
	'annualdividendpershare' => '',
	'dividendpercentbookvalue' => '',
	'dividendpercentmarketvalue' => '',
	'lastupdate' => '',
	'dividendyield' => '',
	'percenttotalbookvalue' => '',
	'percenttotalmarketvalue' => '',
	'percenttotaldividend' => '',
	'idportfolio_history' => '',
	'yield' => '',
	'annualdividend' => '',
	'dividendbookvalue' => '',
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
		include_once( '../model/portfolio_history.class.php' );
		$portfolio_history = new portfolio_history();
		$portfolio_history->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
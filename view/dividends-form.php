<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('dividends');
$form->addElement('text', 'iddividends', 'iddividends: Index', array( 'size' => 11));
$form->addRule( 'iddividends', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'iddividends', 'ERROR: Missing value', 'required');

$form->addElement('text', 'stocksymbol', 'stocksymbol: Stock', array( 'size' => 11));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'stocksymbol', 'ERROR: Missing value', 'required');

$form->addElement('text', 'annualdividend', 'annualdividend: Annual Dividend', array( 'size' => 11));
$form->addRule( 'annualdividend', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'iddividends' => '0',
	'stocksymbol' => '',
	'annualdividend' => '0.00',
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
		include_once( '../model/dividends.class.php' );
		$dividends = new dividends();
		$dividends->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
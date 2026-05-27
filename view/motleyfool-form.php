<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('motleyfool');
$form->addElement('text', 'doubledigitrisingsales', 'doubledigitrisingsales: Is the sales growth at 10 percent or better', array( 'size' => 11));
$form->addRule( 'doubledigitrisingsales', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'risingfreecashflow', 'risingfreecashflow: Is the free cash flow rising', array( 'size' => 11));
$form->addRule( 'risingfreecashflow', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'risingbookvalue', 'risingbookvalue: Is the book value rising', array( 'size' => 11));
$form->addRule( 'risingbookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'improvingmargin', 'improvingmargin: Is their margin improving', array( 'size' => 11));
$form->addRule( 'improvingmargin', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'risingreturnonequity', 'risingreturnonequity: Is the ROE rising', array( 'size' => 11));
$form->addRule( 'risingreturnonequity', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'insiderownership', 'insiderownership: Does the executives own a significant number of shares', array( 'size' => 11));
$form->addRule( 'insiderownership', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'regulardividends', 'regulardividends: Does the company pay dividends consistently', array( 'size' => 11));
$form->addRule( 'regulardividends', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'doubledigitrisingsales', 'doubledigitrisingsales: Is the sales growth at 10 percent or better', array( 'size' => 11));
$form->addRule( 'doubledigitrisingsales', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'risingfreecashflow', 'risingfreecashflow: Is the free cash flow rising', array( 'size' => 11));
$form->addRule( 'risingfreecashflow', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'risingbookvalue', 'risingbookvalue: Is the book value rising', array( 'size' => 11));
$form->addRule( 'risingbookvalue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'improvingmargin', 'improvingmargin: Is their margin improving', array( 'size' => 11));
$form->addRule( 'improvingmargin', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'risingreturnonequity', 'risingreturnonequity: Is the ROE rising', array( 'size' => 11));
$form->addRule( 'risingreturnonequity', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'insiderownership', 'insiderownership: Does the executives own a significant number of shares', array( 'size' => 11));
$form->addRule( 'insiderownership', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'regulardividends', 'regulardividends: Does the company pay dividends consistently', array( 'size' => 11));
$form->addRule( 'regulardividends', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'doubledigitrisingsales' => '',
	'risingfreecashflow' => '',
	'risingbookvalue' => '',
	'improvingmargin' => '',
	'risingreturnonequity' => '',
	'insiderownership' => '',
	'regulardividends' => '',
	'doubledigitrisingsales' => '',
	'risingfreecashflow' => '',
	'risingbookvalue' => '',
	'improvingmargin' => '',
	'risingreturnonequity' => '',
	'insiderownership' => '',
	'regulardividends' => '',
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
		include_once( '../model/motleyfool.class.php' );
		$motleyfool = new motleyfool();
		$motleyfool->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
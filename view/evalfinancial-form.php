<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('evalfinancial');
$form->addElement('text', 'summary', 'summary: Summary (4)', array( 'size' => 11));
$form->addRule( 'summary', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: Company', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'roe', 'roe: Return on Equity', array( 'size' => 11));
$form->addRule( 'roe', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'user', 'user: Evaluating User', array( 'size' => 45));
$form->addRule( 'user', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'user', 'ERROR: Missing value', 'required');

$form->addElement('text', 'retainearningsmv', 'retainearningsmv: Retained Earnings become Market Value', array( 'size' => 11));
$form->addRule( 'retainearningsmv', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'acceptabledebt', 'acceptabledebt: Acceptable Debt Level', array( 'size' => 10));
$form->addRule( 'acceptabledebt', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'lowcost', 'lowcost: Low Cost Operations', array( 'size' => 11));
$form->addRule( 'lowcost', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'summary' => '-1',
	'idstockinfo' => '',
	'roe' => '',
	'user' => '',
	'retainearningsmv' => '',
	'acceptabledebt' => '',
	'lowcost' => '',
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
		include_once( '../model/evalfinancial.class.php' );
		$evalfinancial = new evalfinancial();
		$evalfinancial->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
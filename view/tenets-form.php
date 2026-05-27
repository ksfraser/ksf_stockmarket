<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('tenets');
$form->addElement('text', 'stocksymbol', 'stocksymbol: Company', array( 'size' => 11));
$form->addRule( 'stocksymbol', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'stocksymbol', 'ERROR: Missing value', 'required');

$form->addElement('text', 'simple', 'simple: Simple Business', array( 'size' => 45));
$form->addRule( 'simple', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'simple', 'ERROR: Missing value', 'required');

$form->addElement('text', 'consistent', 'consistent: Consistent Performance', array( 'size' => 45));
$form->addRule( 'consistent', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'consistent', 'ERROR: Missing value', 'required');

$form->addElement('text', 'longterm', 'longterm: Long Term Prospects', array( 'size' => 45));
$form->addRule( 'longterm', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'longterm', 'ERROR: Missing value', 'required');

$form->addElement('text', 'rationalmanager', 'rationalmanager: Rational Management', array( 'size' => 45));
$form->addRule( 'rationalmanager', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'rationalmanager', 'ERROR: Missing value', 'required');

$form->addElement('text', 'candid', 'candid: Candid with Shareholders', array( 'size' => 45));
$form->addRule( 'candid', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'candid', 'ERROR: Missing value', 'required');

$form->addElement('text', 'resistinstitution', 'resistinstitution: Management resists the Institution', array( 'size' => 45));
$form->addRule( 'resistinstitution', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'resistinstitution', 'ERROR: Missing value', 'required');

$form->addElement('text', 'focusroe', 'focusroe: Focus on Return on Equity, not EPS', array( 'size' => 45));
$form->addRule( 'focusroe', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'focusroe', 'ERROR: Missing value', 'required');

$form->addElement('text', 'ownerearnings', 'ownerearnings: Calculated Owner Earnings', array( 'size' => 45));
$form->addRule( 'ownerearnings', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'ownerearnings', 'ERROR: Missing value', 'required');

$form->addElement('text', 'highprofitmargin', 'highprofitmargin: High Profit Margins', array( 'size' => 45));
$form->addRule( 'highprofitmargin', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'highprofitmargin', 'ERROR: Missing value', 'required');

$form->addElement('text', 'retainedtomarket', 'retainedtomarket: Retained Earnings become Market Value', array( 'size' => 45));
$form->addRule( 'retainedtomarket', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'retainedtomarket', 'ERROR: Missing value', 'required');

$form->addElement('text', 'valueofbusiness', 'valueofbusiness: Value of Business', array( 'size' => 45));
$form->addRule( 'valueofbusiness', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'valueofbusiness', 'ERROR: Missing value', 'required');

$form->addElement('text', 'discounted', 'discounted: Purchase at Discount', array( 'size' => 45));
$form->addRule( 'discounted', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'discounted', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'stocksymbol' => 'ABCD',
	'simple' => '',
	'consistent' => '',
	'longterm' => '',
	'rationalmanager' => '',
	'candid' => '',
	'resistinstitution' => '',
	'focusroe' => '',
	'ownerearnings' => '',
	'highprofitmargin' => '',
	'retainedtomarket' => '',
	'valueofbusiness' => '',
	'discounted' => '',
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
		include_once( '../model/tenets.class.php' );
		$tenets = new tenets();
		$tenets->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
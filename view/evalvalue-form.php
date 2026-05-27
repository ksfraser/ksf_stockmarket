<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('evalvalue');
$form->addElement('text', 'idstockinfo', 'idstockinfo: ', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'ownerearnings', 'ownerearnings: ', array( 'size' => 10));
$form->addRule( 'ownerearnings', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'discountrate', 'discountrate: ', array( 'size' => 11));
$form->addRule( 'discountrate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'incomegrowth', 'incomegrowth: year over year growth percentage', array( 'size' => 11));
$form->addRule( 'incomegrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'value', 'value: ', array( 'size' => 11));
$form->addRule( 'value', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'simple', 'simple: ', array( 'size' => 11));
$form->addRule( 'simple', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'valueowners', 'valueowners: ', array( 'size' => 11));
$form->addRule( 'valueowners', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'benefitreinvest', 'benefitreinvest: ', array( 'size' => 11));
$form->addRule( 'benefitreinvest', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'expandbypurchase', 'expandbypurchase: ', array( 'size' => 11));
$form->addRule( 'expandbypurchase', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'regulated', 'regulated: ', array( 'size' => 11));
$form->addRule( 'regulated', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'neededproduct', 'neededproduct: ', array( 'size' => 11));
$form->addRule( 'neededproduct', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'closesubstitute', 'closesubstitute: ', array( 'size' => 11));
$form->addRule( 'closesubstitute', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'mimiccompetition', 'mimiccompetition: ', array( 'size' => 11));
$form->addRule( 'mimiccompetition', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'hyperactivity', 'hyperactivity: ', array( 'size' => 11));
$form->addRule( 'hyperactivity', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'kellyoptimization', 'kellyoptimization: ', array( 'size' => 10));
$form->addRule( 'kellyoptimization', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'riskprobability', 'riskprobability: ', array( 'size' => 10));
$form->addRule( 'riskprobability', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'cosnsistanthistory', 'cosnsistanthistory: ', array( 'size' => 11));
$form->addRule( 'cosnsistanthistory', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'communicatemorethangaap', 'communicatemorethangaap: ', array( 'size' => 11));
$form->addRule( 'communicatemorethangaap', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'publicconfession', 'publicconfession: ', array( 'size' => 11));
$form->addRule( 'publicconfession', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'retainearningsmv', 'retainearningsmv: ', array( 'size' => 11));
$form->addRule( 'retainearningsmv', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'debtratio', 'debtratio: ', array( 'size' => 10));
$form->addRule( 'debtratio', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'acceptabledebt', 'acceptabledebt: ', array( 'size' => 10));
$form->addRule( 'acceptabledebt', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'roe', 'roe: ', array( 'size' => 11));
$form->addRule( 'roe', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'lowcost', 'lowcost: ', array( 'size' => 11));
$form->addRule( 'lowcost', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'frfeqreorg', 'frfeqreorg: ', array( 'size' => 11));
$form->addRule( 'frfeqreorg', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'netincome', 'netincome: ', array( 'size' => 10));
$form->addRule( 'netincome', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'depreciation', 'depreciation: ', array( 'size' => 10));
$form->addRule( 'depreciation', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'depletion', 'depletion: ', array( 'size' => 10));
$form->addRule( 'depletion', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'amortization', 'amortization: ', array( 'size' => 10));
$form->addRule( 'amortization', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'capitalexpenses', 'capitalexpenses: ', array( 'size' => 10));
$form->addRule( 'capitalexpenses', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'workingcapital', 'workingcapital: ', array( 'size' => 10));
$form->addRule( 'workingcapital', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marketcap', 'marketcap: ', array( 'size' => 10));
$form->addRule( 'marketcap', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marginsafety', 'marginsafety: ', array( 'size' => 10));
$form->addRule( 'marginsafety', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'idstockinfo' => '',
	'ownerearnings' => '',
	'discountrate' => '',
	'incomegrowth' => '',
	'value' => '',
	'simple' => '',
	'valueowners' => '',
	'benefitreinvest' => '',
	'expandbypurchase' => '',
	'regulated' => '',
	'neededproduct' => '',
	'closesubstitute' => '',
	'mimiccompetition' => '',
	'hyperactivity' => '',
	'kellyoptimization' => '',
	'riskprobability' => '',
	'cosnsistanthistory' => '',
	'communicatemorethangaap' => '',
	'publicconfession' => '',
	'retainearningsmv' => '',
	'debtratio' => '',
	'acceptabledebt' => '',
	'roe' => '',
	'lowcost' => '',
	'frfeqreorg' => '',
	'netincome' => '',
	'depreciation' => '',
	'depletion' => '',
	'amortization' => '',
	'capitalexpenses' => '',
	'workingcapital' => '',
	'marketcap' => '',
	'marginsafety' => '',
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
		include_once( '../model/evalvalue.class.php' );
		$evalvalue = new evalvalue();
		$evalvalue->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
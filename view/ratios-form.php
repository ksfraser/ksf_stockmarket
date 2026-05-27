<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('ratios');
$form->addElement('text', 'attractivesum', 'attractivesum: Sum of Attractive Scores', array( 'size' => 11));
$form->addRule( 'attractivesum', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'attractiveroa', 'attractiveroa: Is the ROA attractive', array( 'size' => 11));
$form->addRule( 'attractiveroa', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'attractiveroce', 'attractiveroce: is the ROCE attractive', array( 'size' => 11));
$form->addRule( 'attractiveroce', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'attractivegross', 'attractivegross: is the Gross Margin attractive', array( 'size' => 11));
$form->addRule( 'attractivegross', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'attractivepretax', 'attractivepretax: Is the PreTax margin attractive', array( 'size' => 11));
$form->addRule( 'attractivepretax', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'attractivenet', 'attractivenet: Is the Net Margin attractive', array( 'size' => 11));
$form->addRule( 'attractivenet', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'sustaindebtratio', 'sustaindebtratio: Is the debt ratio covered by income long term', array( 'size' => 11));
$form->addRule( 'sustaindebtratio', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: Stock', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'roeattractive', 'roeattractive: Is the ROE attractive (> 15%)', array( 'size' => 11));
$form->addRule( 'roeattractive', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'lowcost', 'lowcost: Low Cost operations (opmargin > .1 )', array( 'size' => 11));
$form->addRule( 'lowcost', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createddate', 'createddate: Created Timestamp', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'debtratio', 'debtratio: Debt Ratio (debt/assets)', array( 'size' => 11));
$form->addRule( 'debtratio', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'acceptabledebtratio', 'acceptabledebtratio: Acceptable Debt Ratio (Net Income/Revenue)', array( 'size' => 11));
$form->addRule( 'acceptabledebtratio', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'roe', 'roe: Return On Equity (Net Income/ Total Equity)', array( 'size' => 11));
$form->addRule( 'roe', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'roa', 'roa: Return On Assets (Net Income / Total Assets)', array( 'size' => 11));
$form->addRule( 'roa', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'operatingmargin', 'operatingmargin: Operating Margin (Operating Income / Revenue )', array( 'size' => 11));
$form->addRule( 'operatingmargin', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'roce', 'roce: Return on Capital Employed (Net Income / Debt + equity)', array( 'size' => 11));
$form->addRule( 'roce', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'grossprofitmargin', 'grossprofitmargin: Gross Profit Margin (Gross Profit/Revenue)', array( 'size' => 11));
$form->addRule( 'grossprofitmargin', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'pretaxmargin', 'pretaxmargin: PreTax Margin (pretax income/revenue)', array( 'size' => 11));
$form->addRule( 'pretaxmargin', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'netmargin', 'netmargin: Net Margin (Net Income / Revenue )', array( 'size' => 11));
$form->addRule( 'netmargin', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateddate', 'updateddate: Updated Timestamp', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createduser', 'createduser: Created by User', array( 'size' => 11));

$form->addElement('text', 'updateduser', 'updateduser: Updated by User', array( 'size' => 11));

$form->addElement('text', 'peratio', 'peratio: Price to Earnings Ratio', array( 'size' => 11));
$form->addRule( 'peratio', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'attractivesum' => '',
	'attractiveroa' => '',
	'attractiveroce' => '',
	'attractivegross' => '',
	'attractivepretax' => '',
	'attractivenet' => '',
	'sustaindebtratio' => '',
	'idstockinfo' => '',
	'roeattractive' => '',
	'lowcost' => '',
	'createddate' => '',
	'debtratio' => '',
	'acceptabledebtratio' => '',
	'roe' => '',
	'roa' => '',
	'operatingmargin' => '',
	'roce' => '',
	'grossprofitmargin' => '',
	'pretaxmargin' => '',
	'netmargin' => '',
	'updateddate' => '',
	'createduser' => '',
	'updateduser' => '',
	'peratio' => '',
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
		include_once( '../model/ratios.class.php' );
		$ratios = new ratios();
		$ratios->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
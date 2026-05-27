<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('fin_statement');
$form->addElement('text', 'dividendpershare1', 'dividendpershare1: dividendpershare last year', array( 'size' => 11));
$form->addRule( 'dividendpershare1', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendpershare2', 'dividendpershare2: dividendpershare 2 years ago', array( 'size' => 11));
$form->addRule( 'dividendpershare2', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'dividendpershare3', 'dividendpershare3: dividendpershare 3 years ago', array( 'size' => 11));
$form->addRule( 'dividendpershare3', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'earningspershare1', 'earningspershare1: earningspershare 1 year ago', array( 'size' => 11));
$form->addRule( 'earningspershare1', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'earningspershare2', 'earningspershare2: earningspershare 2 years ago', array( 'size' => 11));
$form->addRule( 'earningspershare2', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'earningspershare3', 'earningspershare3: earningspershare 3 years ago', array( 'size' => 11));
$form->addRule( 'earningspershare3', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'idstockinfo', 'idstockinfo: Stock', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'lasteval', 'lasteval: Last Evaluated', array( 'size' => 11));
$form->addRule( 'lasteval', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'outstandingshares', 'outstandingshares: Outstanding Common Shares', array( 'size' => 10));
$form->addRule( 'outstandingshares', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'earningpershare', 'earningpershare: Earnings Per Share', array( 'size' => 11));
$form->addRule( 'earningpershare', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'symbol', 'symbol: Stock Symbol', array( 'size' => 11));
$form->addRule( 'symbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'dividendpershare', 'dividendpershare: Annual Dividend Per Share', array( 'size' => 11));
$form->addRule( 'dividendpershare', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'ownerearnings', 'ownerearnings: Owner Earnings', array( 'size' => 11));
$form->addRule( 'ownerearnings', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'retainedearnings', 'retainedearnings: Retained Earnings', array( 'size' => 11));
$form->addRule( 'retainedearnings', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'netincome', 'netincome: Net Income', array( 'size' => 11));
$form->addRule( 'netincome', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'incomegrowth', 'incomegrowth: Year over year Income Growth %', array( 'size' => 11));
$form->addRule( 'incomegrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenue', 'revenue: Revenue', array( 'size' => 11));
$form->addRule( 'revenue', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenuegrowth', 'revenuegrowth: Revenue Growth Compared to 1 Year ago', array( 'size' => 11));
$form->addRule( 'revenuegrowth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenuegrowth2', 'revenuegrowth2: Revenue Growth Compared to 2 Year ago', array( 'size' => 11));
$form->addRule( 'revenuegrowth2', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'revenuegrowth3', 'revenuegrowth3: Revenue Growth Compared to 3 Year ago', array( 'size' => 11));
$form->addRule( 'revenuegrowth3', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totalasset', 'totalasset: Total Assets', array( 'size' => 11));
$form->addRule( 'totalasset', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totalliability', 'totalliability: Total Liabilities', array( 'size' => 11));
$form->addRule( 'totalliability', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totalequity', 'totalequity: Total Equity', array( 'size' => 11));
$form->addRule( 'totalequity', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'totaldebt', 'totaldebt: Total Debt', array( 'size' => 11));
$form->addRule( 'totaldebt', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'depletion', 'depletion: Depletion', array( 'size' => 11));
$form->addRule( 'depletion', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'amortization', 'amortization: Amortization', array( 'size' => 11));
$form->addRule( 'amortization', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'capitalexpenses', 'capitalexpenses: Capital Expenses', array( 'size' => 11));
$form->addRule( 'capitalexpenses', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'workingcapital', 'workingcapital: Change in Working Capital', array( 'size' => 11));
$form->addRule( 'workingcapital', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'user', 'user: Last Evaluation User', array( 'size' => 45));
$form->addRule( 'user', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'dividendpershare1' => '',
	'dividendpershare2' => '',
	'dividendpershare3' => '',
	'earningspershare1' => '',
	'earningspershare2' => '',
	'earningspershare3' => '',
	'idstockinfo' => '',
	'lasteval' => '',
	'outstandingshares' => '',
	'earningpershare' => '0',
	'symbol' => '',
	'dividendpershare' => '0',
	'ownerearnings' => '',
	'retainedearnings' => '0',
	'netincome' => '',
	'incomegrowth' => '',
	'revenue' => '0',
	'revenuegrowth' => '',
	'revenuegrowth2' => '',
	'revenuegrowth3' => '',
	'totalasset' => '',
	'totalliability' => '',
	'totalequity' => '',
	'totaldebt' => '',
	'depletion' => '',
	'amortization' => '',
	'capitalexpenses' => '',
	'workingcapital' => '',
	'user' => '',
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
		include_once( '../model/fin_statement.class.php' );
		$fin_statement = new fin_statement();
		$fin_statement->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
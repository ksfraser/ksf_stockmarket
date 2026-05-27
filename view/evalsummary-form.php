<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('evalsummary');
$form->addElement('text', 'idstockinfo', 'idstockinfo: Stock Symbol', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'idstockinfo', 'ERROR: Missing value', 'required');

$form->addElement('text', 'totalscore', 'totalscore: Total of Scores (36)', array( 'size' => 11));
$form->addRule( 'totalscore', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'totalscore', 'ERROR: Missing value', 'required');

$form->addElement('hidden', 'reviseddate', 'reviseddate: Last Revision Date', array( 'size' => 17));
$form->addRule( 'reviseddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'marginsafety', 'marginsafety: Margin of Safety (%)', array( 'size' => 11));
$form->addRule( 'marginsafety', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'marginsafety', 'ERROR: Missing value', 'required');

$form->addElement('text', 'ratioscore', 'ratioscore: Score from Ratios table (8)', array( 'size' => 11));
$form->addRule( 'ratioscore', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'iplacecalcscore', 'iplacecalcscore: Score from iplace_calc (10)', array( 'size' => 11));
$form->addRule( 'iplacecalcscore', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'managementscore', 'managementscore: Management Tenets score (9)', array( 'size' => 11));
$form->addRule( 'managementscore', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'managementscore', 'ERROR: Missing value', 'required');

$form->addElement('text', 'financialscore', 'financialscore: Financial Tenets score (4)', array( 'size' => 11));
$form->addRule( 'financialscore', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'financialscore', 'ERROR: Missing value', 'required');

$form->addElement('text', 'businessscore', 'businessscore: Business Tenets score (5)', array( 'size' => 11));
$form->addRule( 'businessscore', 'ERROR: Incorrect data type', 'numeric');
$form->addRule( 'businessscore', 'ERROR: Missing value', 'required');

$form->addElement('hidden', 'reviseduser', 'reviseduser: Revised by User', array( 'size' => 45));
$form->addRule( 'reviseduser', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'idstockinfo' => '',
	'totalscore' => '-1',
	'reviseddate' => '',
	'marginsafety' => '-999999',
	'ratioscore' => '',
	'iplacecalcscore' => '',
	'managementscore' => '-1',
	'financialscore' => '-1',
	'businessscore' => '-1',
	'reviseduser' => '',
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
		include_once( '../model/evalsummary.class.php' );
		$evalsummary = new evalsummary();
		$evalsummary->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
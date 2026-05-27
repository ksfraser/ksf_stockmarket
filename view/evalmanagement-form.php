<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('evalmanagement');
$form->addElement('text', 'idstockinfo', 'idstockinfo: Corporation', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'managementowners', 'managementowners: Management are shareholders', array( 'size' => 11));
$form->addRule( 'managementowners', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'benefitreinvest', 'benefitreinvest: Beneficial Reinvestment of Earnings', array( 'size' => 11));
$form->addRule( 'benefitreinvest', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'expandbypurchase', 'expandbypurchase: Expands the business through acquisitions', array( 'size' => 11));
$form->addRule( 'expandbypurchase', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'mimiccompetition', 'mimiccompetition: Management mimics the compeition (Lemmings)', array( 'size' => 11));
$form->addRule( 'mimiccompetition', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'hyperactivity', 'hyperactivity: Hyperactive Management', array( 'size' => 11));
$form->addRule( 'hyperactivity', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'cosnsistanthistory', 'cosnsistanthistory: Consistent Operating History (Predictability)', array( 'size' => 11));
$form->addRule( 'cosnsistanthistory', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'communicatemorethangaap', 'communicatemorethangaap: Management Communicates more than just GAAP', array( 'size' => 11));
$form->addRule( 'communicatemorethangaap', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'publicconfession', 'publicconfession: Confesses errors in public', array( 'size' => 11));
$form->addRule( 'publicconfession', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'frfeqreorg', 'frfeqreorg: Frequent Re-orgs and Cost Cutting announcements', array( 'size' => 11));
$form->addRule( 'frfeqreorg', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'user', 'user: Evaluating User', array( 'size' => 45));
$form->addRule( 'user', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'user', 'ERROR: Missing value', 'required');

$form->setDefaults( array(
	'idstockinfo' => '',
	'managementowners' => '',
	'benefitreinvest' => '',
	'expandbypurchase' => '',
	'mimiccompetition' => '',
	'hyperactivity' => '',
	'cosnsistanthistory' => '',
	'communicatemorethangaap' => '',
	'publicconfession' => '',
	'frfeqreorg' => '',
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
		include_once( '../model/evalmanagement.class.php' );
		$evalmanagement = new evalmanagement();
		$evalmanagement->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
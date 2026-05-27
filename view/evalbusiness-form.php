<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('evalbusiness');
$form->addElement('text', 'idstockinfo', 'idstockinfo: Company', array( 'size' => 11));
$form->addRule( 'idstockinfo', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'user', 'user: Evaluating User', array( 'size' => 45));
$form->addRule( 'user', 'ERROR: Incorrect data type', 'alphanumeric');
$form->addRule( 'user', 'ERROR: Missing value', 'required');

$form->addElement('text', 'simple', 'simple: Simple Business', array( 'size' => 11));
$form->addRule( 'simple', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'cosnsistanthistory', 'cosnsistanthistory: Consistent Performance', array( 'size' => 11));
$form->addRule( 'cosnsistanthistory', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'neededproduct', 'neededproduct: Needed Product', array( 'size' => 11));
$form->addRule( 'neededproduct', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'noclosesubstitute', 'noclosesubstitute: No close substitute of Product', array( 'size' => 11));
$form->addRule( 'noclosesubstitute', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'regulated', 'regulated: Regulated Industry', array( 'size' => 11));
$form->addRule( 'regulated', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'idstockinfo' => '',
	'user' => '',
	'simple' => '',
	'cosnsistanthistory' => '',
	'neededproduct' => '',
	'noclosesubstitute' => '',
	'regulated' => '',
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
		include_once( '../model/evalbusiness.class.php' );
		$evalbusiness = new evalbusiness();
		$evalbusiness->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
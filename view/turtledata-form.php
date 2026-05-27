<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('turtledata');
$form->addElement('text', 'idturtledata', 'idturtledata: Index of table', array( 'size' => 11));
$form->addRule( 'idturtledata', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'createddate', 'createddate: Date the record was created', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createduser', 'createduser: Record created by user', array( 'size' => 11));
$form->addRule( 'createduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateddate', 'updateddate: date record was updated', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateduser', 'updateduser: record updated by user', array( 'size' => 11));
$form->addRule( 'updateduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'volatility', 'volatility: The volatility (N) of the market', array( 'size' => 11));
$form->addRule( 'volatility', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'unit', 'unit: The unit size of the market', array( 'size' => 11));
$form->addRule( 'unit', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'breakouthigh20', 'breakouthigh20: The 20 day high breakout value', array( 'size' => 11));
$form->addRule( 'breakouthigh20', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'breakoutlow20', 'breakoutlow20: The low 20 day breakout price', array( 'size' => 11));
$form->addRule( 'breakoutlow20', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'breakouthigh55', 'breakouthigh55: The high 55 day breakout price', array( 'size' => 11));
$form->addRule( 'breakouthigh55', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'breakoutlow55', 'breakoutlow55: The 55 day low breakout value', array( 'size' => 11));
$form->addRule( 'breakoutlow55', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'low10', 'low10: The 10 day low for selling longs', array( 'size' => 11));
$form->addRule( 'low10', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'high10', 'high10: The 10 day high used for selling shorts', array( 'size' => 11));
$form->addRule( 'high10', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'low20', 'low20: The 20 day low price', array( 'size' => 11));
$form->addRule( 'low20', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'high20', 'high20: The 20 day high price', array( 'size' => 11));
$form->addRule( 'high20', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'truerange', 'truerange: True range - MAX( High0-Low0, High0-Close1, Close1 - Low0 )', array( 'size' => 11));
$form->addRule( 'truerange', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'ignore20', 'ignore20: Was the 20 day signal ignored due to the winning trade rule', array( 'size' => 11));
$form->addRule( 'ignore20', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'positionadd', 'positionadd: Once a breakout occurs, you can add to the position at 1/2N prices.  What is the next 1/2N price', array( 'size' => 11));
$form->addRule( 'positionadd', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'sellallprice', 'sellallprice: All units are sold if the breakout20 is reached before the 10 day exit price', array( 'size' => 11));
$form->addRule( 'sellallprice', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'normalizedprice', 'normalizedprice: Normalized price of the market - Current Price - 90day EMA divided by N', array( 'size' => 11));
$form->addRule( 'normalizedprice', 'ERROR: Incorrect data type', 'numeric');

$form->setDefaults( array(
	'idturtledata' => '',
	'createddate' => '',
	'createduser' => '',
	'updateddate' => '',
	'updateduser' => '',
	'volatility' => '',
	'unit' => '',
	'breakouthigh20' => '',
	'breakoutlow20' => '',
	'breakouthigh55' => '',
	'breakoutlow55' => '',
	'low10' => '',
	'high10' => '',
	'low20' => '',
	'high20' => '',
	'truerange' => '',
	'ignore20' => '',
	'positionadd' => '',
	'sellallprice' => '',
	'normalizedprice' => '',
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
		include_once( '../model/turtledata.class.php' );
		$turtledata = new turtledata();
		$turtledata->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
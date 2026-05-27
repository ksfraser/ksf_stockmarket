<?
//20090102 Eventum project financial issue #38
//Trigger an alert only once

//require_once( 'data/generictable.php');
//require_once( '../local.php' );
//Local_Init();
//require_once( 'security/genericsecurity.php');
//global $Security;
echo __FILE__;
require_once( 'include_all.php' );

require_once( 'alerts.php' );
require_once( $MODELDIR . '/stockalert.class.php' );
require_once( $MODELDIR . '/alerts.class.php' );
require_once( $MODELDIR . '/alertsraised.class.php' );

$alert = new alerts();
$alertsraised = new alertsraised();
$stockalert = new stockalert();
//Eventum project finance issue #38
$updatestockalert = new stockalert();
$stockalert->where = "runonce = 1 and runstatus = 0";
//!#38
$stockalert->Select();
foreach( $stockalert->resultarray as $result )
{
//	var_dump( $result );
	$alert->where = "idalerts = '" . $result['idalerts'] . "'";
	$alert->Select();
//	var_dump( $alert->resultarray );
	if( is_callable( $alert->resultarray[0]['alertfunctionname'] ) )
	{
//		echo "Alert " . $alert->resultarray[0]['alertfunctionname'] . " Callable\n";
		//var_dump( $alert->resultarray[0]['alertfunctionname']);
		//echo "Calling:....\n";
		//var_dump( $result );
		$result = $alert->resultarray[0]['alertfunctionname']( $result['username'], $result['idstockinfo'], $result['value1'], $result['value2'] );
		if ($result == 1)
		{
			//echo "Alert Raised\n";
			//Alert was raised
			$insert['username'] = $result['username']; 
			$insert['idalerts'] = $result['idalerts'];
			$insert['idstockalert'] = $result['idstockalert'];
			$alertsraised->Insert( $insert );
			//Eventum project finance issue #38
			//Update the stockalert runstatus
			$update['username'] = $result['username']; 
			$update['idalerts'] = $result['idalerts'];
			$update['idstockinfo'] = $result['idstockinfo'];
			$update['idstockalert'] = $result['idstockalert'];
			$update['runstatus'] = 1;
			$updatestockalert->Update( $update );
			//!#38
		}
	//	else
			//echo "Alert NOT Raised\n";
	}
	else
	{
//		echo "Alert " . $alert->resultarray[0]['alertfunctionname'] . " Not Callable\n";
	}
	
}
$stockalert->where = "runonce = 0";
//!#38
$stockalert->Select();
foreach( $stockalert->resultarray as $result )
{
//	var_dump( $result );
	$alert->where = "idalerts = '" . $result['idalerts'] . "'";
	$alert->Select();
//	var_dump( $alert->resultarray );
	if( is_callable( $alert->resultarray[0]['alertfunctionname'] ) )
	{
//		echo "Alert " . $alert->resultarray[0]['alertfunctionname'] . " Callable\n";
		//var_dump( $alert->resultarray[0]['alertfunctionname']);
		//echo "Calling:....\n";
		//var_dump( $result );
		$result = $alert->resultarray[0]['alertfunctionname']( $result['username'], $result['idstockinfo'], $result['value1'], $result['value2'] );
		if ($result == 1)
		{
			//echo "Alert Raised\n";
			//Alert was raised
			$insert['username'] = $result['username']; 
			$insert['idalerts'] = $result['idalerts'];
			$insert['idstockalert'] = $result['idstockalert'];
			$alertsraised->Insert( $insert );
		}
	//	else
			//echo "Alert NOT Raised\n";
	}
	else
	{
//		echo "Alert " . $alert->resultarray[0]['alertfunctionname'] . " Not Callable\n";
	}
	
}


?>

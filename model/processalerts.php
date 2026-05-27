<?
//20090102 Eventum project financial issue #38
//Trigger an alert only once

require_once( 'data/generictable.php');
require_once( '../local.php' );
Local_Init();
require_once( 'security/genericsecurity.php');
global $Security;

require_once( '../scripts/alerts.php' );
require_once( 'stockalert.class.php' );
require_once( 'alerts.class.php' );
require_once( 'alertsraised.class.php' );

$alert = new alerts();
$alertsraised = new alertsraised();
$stockalert = new stockalert();
//Eventum project finance issue #38
$updatestockalert = new stockalert();
//$stockalert->where = "runonce <> 1 and runstatus <> 1";
//!#38
//$stockalert->nolimit = TRUE;
//$stockalert->limit=9999;
$stockalert->Select();
echo "Processing " . count($stockalert->resultarray ) . " alerts\n";
foreach( $stockalert->resultarray as $result )
{
//	var_dump( $result );
	$alert->where = "idalerts = '" . $result['idalerts'] . "'";
	$alert->Select();
//	var_dump( $alert->resultarray );
	if( is_callable( $alert->resultarray[0]['alertfunctionname'] ) )
	{
		echo "Running " . $alert->resultarray[0]['alertfunctionname'] . " for " . $result['username'] . "\n";
		$result = $alert->resultarray[0]['alertfunctionname']( $result['username'], $result['idstockinfo'], $result['value1'], $result['value2'] );
		if ($result == 1)
		{
			//Alert was raised
			$insert['username'] = $result['username']; 
			$insert['idalerts'] = $result['idalerts'];
			$insert['idstockalert'] = $result['idstockalerts'];
			$alertsraised->Insert( $insert );
			//Eventum project finance issue #38
			//Update the stockalert runstatus
			$update['idstockalert'] = $result['idstockalert'];
			$update['runstatus'] = 1;
			$updatestockalert->Update( $update );
			//!#38
		}
	}
	else
		echo "Can't process " . $alert->resultarray[0]['alertfunctionname'] . "\n";
}


?>

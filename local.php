<?php

//this script may only be included - so its better to die if called directly.
if (strpos($_SERVER["SCRIPT_NAME"],basename(__FILE__)) !== false) {
header("location: index.php");
exit;
}

$realm = "finance";
$baseurl="/finance/";
$pathlen = strlen( __FILE__ );
$namelen = strlen( basename( __FILE__ ) );
/*
//20091006 KF docroot assuming /var/www/html.  This results in bad menu paths if
//the directory is somewhere else and conf.d/appname.conf aliased
//script_filename and script_name seem to be more accurate
*/
$docrootlen = strlen( $_SERVER['DOCUMENT_ROOT'] );
$scriptlen = strlen( $_SERVER['SCRIPT_NAME'] );
$path = __FILE__;
/*
	echo "Pathlen: $pathlen :: Path: $path :: Namelen: $namelen :: DocrootLen: $docrootlen::\n";
	echo "<br />";
	var_dump( $_SERVER );
	echo "<br />";
	echo substr( $path, $docrootlen );
	echo "<br />";
	echo substr( $path, $docrootlen, $pathlen );
	echo "<br />";
	echo substr( $path, $docrootlen, $pathlen - $namelen - $docrootlen );
	echo "<br />";
	echo "DIRNAME __FILE__: " . dirname( __FILE__ ) . "<br />";
	echo "DIRNAME __SELF__: " . dirname( $_SERVER['PHP_SELF'] ) . "<br />";
	echo " __DocRoot__: " .  $_SERVER['DOCUMENT_ROOT'] . "<br />";
*/

if ( $_SERVER['DOCUMENT_ROOT'] == ( dirname( __FILE__ ) . "/" ) )
{
	//Called from a virtual server with its own doc root
	//echo "NO SUBSTRING<br />";
	$appdir = ".";
	$cssdir = "/stylesheets/";
	//$cssdir = ".";
}
else
{
	//$appdir = substr( $path, $docrootlen, $pathlen - $namelen - $docrootlen - 1 );
	//$appdir = substr( $path, $docrootlen, $scriptlen - 1 );
	//$appdir = substr( $path, $scriptlen, $pathlen - $namelen - $docrootlen - 1 );
	//$appdir = substr( $path, $scriptlen,  - 1 );
	$appdir = dirname( $_SERVER['PHP_SELF'] );
	$cssdir = substr( $path, $docrootlen, $pathlen - $namelen - $docrootlen - 1 );
	$cssdir = "/stylesheets/";
	//$cssdir = ".";
}
/*
echo "Appdir: $appdir <br />";
echo "\n" . $path . "<br />\n" . $appdir . "<br />\n";
echo $pathlen;
echo "<br />\n";
echo $namelen;
echo "<br />\n";
echo $docrootlen;
echo "<br />\n";
*/

$railroadnumber = 1;

define( "WHOAMI", "01" );
define( "CENTRAL", "00" );
define( "LOGLEVEL", "insertupdatedelete" ); //log deletes from the db
define( "TRACELEVEL", "errorwarnflow" ); //Log to screen errors, warnings, proc flow

define ("SUCCESS", 1);
define("NOSMARTY", 1);
define( "FAILURE", 2 );

//Logging levels
/*
PEAR_LOG_EMERG 	emerg() 	System is unusable
PEAR_LOG_ALERT 	alert() 	Immediate action required
PEAR_LOG_CRIT 	crit() 	Critical conditions
PEAR_LOG_ERR 	err() 	Error conditions
PEAR_LOG_WARNING 	warning() 	Warning conditions
PEAR_LOG_NOTICE 	notice() 	Normal but significant
PEAR_LOG_INFO 	info() 	Informational
PEAR_LOG_DEBUG 	debug() 	Debug-level messages
*/
define( "Log_Default_Level", 'PEAR_LOG_WARN' );
//define( "Backtest_Log_Default_Level", 'PEAR_LOG_DEBUG' );
define( "Backtest_Log_Default_Level", 'PEAR_LOG_NOTICE' );
define( "Log_Max_Level", 'PEAR_LOG_EMERG' );
define( "Log_Min_Level", 'PEAR_LOG_DEBUG' );
define( "MM_truerangefactor", '2' );
define( 'BUY', 10 );
define( 'SELL', 20 );
define( 'HOLD', 30 );
define( 'SHORT', 40 );
define( 'COVER', 50 );
define( 'MM_Maxrisk', 1 );
define( 'MM_SingleTradeRisk', 10 );

//Shortest normal barcode is 7 characters long
define( "MINBARCODELEN", 7 ); 
$viewdir = "view/";
$datadir = "data/";
$classdir = "model/";
//define ( "APPDIR", $DIR );
define ( "APPDIR", dirname( __FILE__ ) );
//define ( "APPDIR", "YOP" );
//echo APPDIR;
define ( "BASEDIR", dirname( __FILE__ ) );
define ( "VIEWDIR", APPDIR . "/view" );
define ( "DATADIR", APPDIR . "/data" );
define ( "CLASSDIR", APPDIR . "/model" );
define ( "MODELDIR", APPDIR . "/model" );
define ( "REPORTDIR", APPDIR . "/reports" );
define ( "SCRIPTDIR", APPDIR . "/scripts" );
define ( "LOGDIR", APPDIR . "/logs" );
//echo "<br />" . MODELDIR . "<br />";
$MODELDIR = MODELDIR;
$APPDIR = APPDIR;
require_once( $datadir . 'db.php');

	function Local_DB()
	{
                //$db = new my_db( 'localhost', 'investing', 'investing', 'stocks');
                $db = new my_db( '192.168.1.14', 'finance', 'finance', 'finance');
		return $db;
	}

	function menufromls($listingkey = ".")
	{
		$menutable = '<div class="mtable"><table border=2>';
		if ($dh = opendir("."))
		{
//		echo "in dir\n";
			while (($file = readdir($dh)) !== false)
			{
//			echo "read dir, searching for $listingkey, in filename $file\n";
				if (stristr($file, $listingkey) != false )
				{
				"File $file\n";
					$menutable .= '<tr><td><a href="' . $file . '">' . $file . '</a></td></tr>';
				}
				else
				{
			//		echo "$file did not match $listingkey\n";
				}
			}
		}
		$menutable .= '</table></div>';
		return $menutable;
	}

	function CSS()
	{
		return;
	}

function Local_Menu()
{
//	echo "LOCALMENU CSS<br />";
	$menucss = CSS();
	$menu = NULL;
//	echo "LOCALMENU<br />";
	//$menuls = menufromls(".list.php");
	//$menuls .= menufromls(".insert.php");
	//$menuls .= menufromls(".update.php");
	//$menuls .= menufromls(".delete.php");
	//$menuls .= menufromls(".search.php");
//	echo "LOCALMENU ATOMIC<br />";
	require_once( 'view/atomic.php' );
	//$menu = new atomic($menuls);
	//echo "LOCALMENU POST ATOMIC<br />";
	return $menu;
}

function Local_Init()
{
	error_reporting(E_ALL);
//	display_errors(OFF);
//	log_errors(ON);
	error_log('syslog');
}
	
	
?>

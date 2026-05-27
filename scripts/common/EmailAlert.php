<?php

echo __FILE__;

require_once( $MODELDIR . '/include_all.php' );
//require_once( $MODELDIR . '/users.class.php' );
require_once( 'security/users.class.php' );

function EmailAlert( $username, $header, $msg )
{
	$user = new users();
	$user->where = "username = '" . $username . "'";
	$user->Select();
	$mailto = $user->resultarray[0]['emailaddress'];
	if( isset( $mailto ) )
	{
		//EMAIL HERE
		echo "Email to " . $mailto . " Msg $msg";
		mail( $mailto, $header, $msg );
		return SUCCESS;
	}
	return FAILURE;
}



?>

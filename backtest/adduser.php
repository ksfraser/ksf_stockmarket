<?php

//20090804 KF
//Add users to tool for backtesting purposes

function adduser( $flog, $username, $surname = "Testing", $firstname = "Backtest", $emailaddress = "fraser.ks@gmail.com", $password = "", $roles_id = "00000000002" )
{
	if( require_once( '../model/users.class.php' ))
	{
		$insert['username'] = $username;
		$insert['surname'] = $surname;
		$insert['firstname'] = $firstname;
		$insert['emailaddress'] = $emailaddress;
		$insert['password'] = $password;
		$insert['roles_id'] = $roles_id;

		$users = new users();
		$users->where = "username = '$username'";
		$users->Select();
		if( $users->resultarray[0]['username'] == $username )
		{
			fwrite( $flog, "Updating user $username\n" );
			$users->Update( $insert );
		}
		else
		{	
			fwrite( $flog, "Adding user $username\n" );
			$users->Insert( $insert );
		}
		return SUCCESS;
	}
	return FAILURE;
}



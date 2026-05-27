<?php


	
class Form
{
	var $table;
	var $numtable;
	var $action;
	var $method;
	function SetTable($newtable)
	{
		$this->numtable = $this->numtable + 1;
	//	$this->table[$this->numtable] = $newtable;
		$this->table = $newtable;
	}
	function SetEntry($entry)
	{
		$this->SetTable($entry);
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		$ret = '';
		$ret .= ' <form action="' . $this->action . '" method=' . $this->method . '>';
//		for ($i = 1; $i <= $numtable; $i++)
//		{
//		  $this->table[$i]->Display();
//		}
		$ret .= $this->table->ReturnDisplay();
		$ret .='<tr><td colspan=2 align=center><input type=submit value="Submit" /></td></tr>';
		$ret .= '</form>';
		return $ret;
	}
	function form($action = "", $method = "POST")
	{
		if ($action == "")
		{
			$action = $_SERVER['PHP_SELF'];
		}
		$this->numtable = 0;
		$this->action = $action;
		$this->method = $method;
	}
}

?>

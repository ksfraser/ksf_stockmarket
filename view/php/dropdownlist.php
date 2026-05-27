<?php

	
class DropDownList
{
	var $name;
	var $option;
	var $numoption;
	var $displaytext;
	function DropDownList()
	{
		$this->numoption = 0;
	}
	function SetOption($newoption)
	{
		//Zero based array
		$this->option[$this->numoption] = $newoption;
		$this->numoption = $this->numoption + 1;
	}
	function SetDisplaytext($text)
	{
		$this->displaytext = $text;
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function Display()
	{
		$ret = "";
		//echo( '<td>' . $this->displaytext . '</td>');		
		//echo ('<td><select name=' . $this->name . '>');
		$ret .= '<td>' . $this->displaytext . '</td>';		
		$ret .= '<td><select name=' . $this->name . '>';
		for ($i = 0; $i < $this->numoption; $i++)
		{
		  $this->option[$i]->Display();
		  $ret .= $this->option[$i]->Display();
		}
		//echo ('</select></td>');
		$ret .= '</select></td>';
		return $ret;

	}
	function ReturnDisplay()
	{
//Depreciated - moved into DISPLAY
		return $this->Display();
	}
}

class DropDownOption
{
	var $value;
	var $displaytext;
	function DropDownOption($text = "", $value = "")
	{
		$this->SetValue($value);
		$this->SetDisplaytext($text);
	}
	function SetValue($value)
	{
		$this->value = $value;
	}
	function SetDisplaytext($text)
	{
		$this->displaytext = $text;
	}
	function Display()
	{
		//echo ('<option value="' . $this->value . '">' . $this->displaytext);
		$ret = '<option value="' . $this->value . '">' . $this->displaytext;
		return $ret;
	}
	function ReturnDisplay()
	{
//Depreciate - moved into Display	
		return $this->Display();
	}
}
?>

<?php

class Entry
{
	var $displaytext;
	var $inputtype;
	var $name;
	var $size;
	var $maxlength;
	var $value;
	function SetDisplaytext($newentry)
	{
		$this->displaytext = $newentry;
	}
	function SetInputtype($newentry)
	{
		$this->inputtype = $newentry;
	}
	function SetName($newentry)
	{
		$this->name = $newentry;
	}
	function SetSize($newentry)
	{
		$this->size = $newentry;
	}
	function SetMaxlength($newentry)
	{
		$this->maxlength = $newentry;
	}
	function entry($text, $type, $name, $size = 16, $maxlength = 16, $defaultvalue = "")
	{
		$this->SetDisplaytext($text);
		$this->SetInputtype($type);
		$this->SetName($name);
		$this->SetSize($size);
		$this->SetMaxlength($maxlength);
		$this->value = $defaultvalue;
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		$ret = '<td>' . $this->displaytext . '</td> <td><input type=' . $this->inputtype . ' name=' . $this->name . ' size=' . $this->size . ' maxlength=' . $this->maxlength . ' value="' . $this->value . '"></td>';
		return $ret;
	}
   
}

?>

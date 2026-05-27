<?php
class atomic
{
	var $item;
	var $starttag;
	var $endtag;
	function atomic($item = "", $starttag = "", $endtag = "")
	{
		$this->item = $item;
		$this->starttag = $starttag;
		$this->endtag = $endtag;
	}
	function SetItem($item)
	{
		$this->item = $item;
		return SUCCESS;
	}
	function Display()
	{
		if (NOSMARTY)
		{
			return $this->starttag . $this->item . $this->endtag;
		}
	}

}

?>

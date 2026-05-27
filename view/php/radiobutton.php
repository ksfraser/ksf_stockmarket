<?php
	require_once('atomic.php');


	class radiobutton extends atomic
	{
		var $name;
		var $value;
		var $align;
		var $tabindex;
		var $checked;

		function radiobutton($name = "SET ME", $value = "SET ME", $checked = "NO", $align = "left", $tabindex = NULL)
		{
			$this->name = $name;
			$this->value = $value;
			$this->align = $align;
			$this->tabindex = $tabindex;
			$this->checked = $checked;
			$this->starttag = '<input type="radio" name="' . $this->name . '" value="' . $this->value . '" align="' . $this->align . '"';
			if ( ($checked == "YES") OR ($checked == "CHECKED") )
			{
				$this->starttag .= " checked";
			}
			if ($tabindex)
			{
				$this->starttag .= ' tabindex="' . $this->tabindex . '"';
			}
			$this->starttag .= ">";
			$this->endtag = "<br />";
			$this->item = $value;
			return;
		}
	}

?>

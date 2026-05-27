<?php

	require_once('tablerows.php');
	require_once('tableinputs.php');
	require_once('dropdownlist.php');
	require_once('entry.php');
class Table
{
	var $entry;	//Should this be depreciated?
	var $numentry;
	var $button;
	var $numbutton;
	var $cellpadding;
	var $cellspacing;
	var $bgcolor;
	var $width;
	var $frame;
	var $rules;
	var $border;
	var $header;
	var $thead;	//This should be a row
	var $tfoot;	//This should be a row
	var $tbody;	//This should be a row
	var $tmain;
	var $rowspan;
	var $colspan;
	var $tbodycount;
	function SetColspan($col)
	{
		$this->colspan = $col;
	}
	function SetRowspan($row)
	{
		$this->rowspan = $row;
	}
	function SetTHead($header)
	{
		$this->thead = $header;
	}
	function SetTFoot($foot)
	{
		$this->tfoot = $foot;
	}
	function SetTMain($body)
	{
		$this->tmain = $body;
	}
	function SetTBody($body)
	{
		$this->tbody = $body;
		$this->tbodycount = 1;
	}
	function SetHeader($header)
	{
		$this->header = $header;
	}
	function SetBorder($border)
	{
		$this->border = $border;
	}
	function SetRules($rules)
	{
		$this->rules = $rules;
	}
	function SetFrame($frame)
	{
		$this->frame = $frame;
	}
	function SetEntry($newentry)
	{
		$this->numentry = $this->numentry + 1;
		$this->entry[$this->numentry] = $newentry;
	}
	function SetButton($newbutton)
	{
		$this->numbutton = $this->numbutton + 1;
		$this->button[$this->numbutton] = $newbutton;
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		$ret = '<table ';
		if ($this->width)
	          $ret .= ' width=' . $this->width;
		if ($this->border)  
	          $ret .= ' border=' . $this->border;
		if ($this->bgcolor)
	          $ret .= ' bgcolor=' . $this->bgcolor;
		if ($this->cellpadding)  
	          $ret .= ' cellpadding=' . $this->cellpadding;
		if ($this->cellspacing)  
	        $ret .= ' cellspacing=' . $this->cellspacing ;
		$ret .= '>';
		if ($this->thead)
		{
		  $ret .= ('<thead>');
		  $ret .= $this->thead->Display();
		  $ret .= ('</thead>');
		}
		if ($this->tfoot)
		{
		  $ret .= ('<tfoot>');
		  $ret .= $this->tfoot->Display();
		  $ret .= ('</tfoot>');
		}
		if ($this->tmain)
		{
		  $ret .= ('<tbody>');
		  $ret .= $this->tbody->Display();
		  $ret .= ('</tbody>');
		}
		if ($this->tbodycount > 0)
		{
		  $ret .= ('<tbody>');
		  $ret .= $this->tbody->Display();
		  $ret .= ('</tbody>');
	        }

		for ($i = 1; $i <= $this->numentry; $i++)
		{
		  $ret .= $this->entry[$i]->Display();
		}
		for ($i = 1; $i <= $this->numbutton; $i++)
		{
		  $ret .= $this->button[$i]->Display();
		}
		
   		$ret .= '</table>';
		return $ret;
	}
	function Table($width = "99%", $cellpadding = 2, $cellspacing = 0, $bgcolor = "#cccccc")
	{
		$this->numentry = 0;
		$this->width = $width;
		$this->cellpadding = $cellpadding;
		$this->cellspacing = $cellspacing;
		$this->bgcolor = $bgcolor;
		$this->tbodycount = 0;

		//$this->tbody = new TBody();
		//$this->thead = new TBody();
		//$this->tfoot = new TBody();
		//$this->tmain = new TBody();
	}
}

?>

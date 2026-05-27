<?php  



class InputCell
{
	//
	function Cell()
	{
		$this->__constructor();
	}
	function __constructor($text)
	{
		$this->text = $text;
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		return $this->text->ReturnDisplay();
	}
}

	
class Cell
{
	var $text;
	var $starttag;
	var $endtag;
	//
	function Cell($text, $starttag = "", $endtag = "")
	{
		$this->__constructor($text, $starttag, $endtag);
		return;
	}
	function __constructor($text, $starttag = "", $endtag = "")
	{
		$this->text = $text;
		$this->SetStartTag($starttag);
		$this->SetEndTag($endtag);
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		return $this->starttag . $this->text . $this->endtag;
	}
	function SetStartTag($tag)
	{
		$this->starttag = $tag;
		return;
	}
	function SetEndTag($tag)
	{
		$this->endtag = $tag;
	}
}

class RowHeaderCell extends Cell
{
	function RowHeaderCell($text)
	{
		return parent::__constructor($text, "<th>", "</th>");
		
	}
}

class RowDataCell extends Cell
{
	var $COLSPAN;
	var $ROWSPAN;
	var $ALIGN;
	var $VALIGN;
	function RowDataCell($COLSPAN = 1, $ROWSPAN = 1, $ALIGN = "CENTER", $VALIGN = "CENTER", $text = "")
	{
		$this->COLSPAN = $COLSPAN;
		$this->ROWSPAN = $ROWSPAN;
		$this->ALIGN = $ALIGN;
		$this->VALIGN = $VALIGN;
		$this->text = $text;
	}
	function ReturnDisplay()
	{
//Depreciated
	return '<td COLSPAN=' . $this->COLSPAN . ' ROWSPAN=' . $this->ROWSPAN .' ALIGN=' . $this->ALIGN . ' VALIGN=' . $this->VALIGN . '>' . $this->text . '</td>';
	}
}


class RowCell
{
	//Intent is to use for encapsulating tables in tables
	var $displaytext;
	var $option;
	var $numoption;
	var $COLSPAN;
	var $ROWSPAN;
	var $ALIGN;
	var $VALIGN;
	function RowCell($COLSPAN = 1, $ROWSPAN = 1, $ALIGN = "CENTER", $VALIGN = "CENTER", $text = "")
	{
		$this->COLSPAN = $COLSPAN;
		$this->ROWSPAN = $ROWSPAN;
		$this->ALIGN = $ALIGN;
		$this->VALIGN = $VALIGN;
		$this->numoption = 0;
		$this->displaytext = $text;
	}
	function SetOption($newoption)
	{
		$this->numoption = $this->numoption + 1;
		$this->option[$this->numoption] = $newoption;
	}
	function SetDisplayText($text)
	{
		$this->displaytext = $text;
	}
	function Display()
	{
		$ret = "";
		for ($i = 1; $i <= $this->numoption; $i++)
		{
		//echo ('<td COLSPAN=' . $this->COLSPAN . ' ROWSPAN=' . $this->ROWSPAN .' ALIGN=' . $this->ALIGN . ' VALIGN=' . $this->VALIGN . '>' . $this->option[$i]->Display() . '</td>');
			$ret .= '<td COLSPAN=' . $this->COLSPAN . ' ROWSPAN=' . $this->ROWSPAN .' ALIGN=' . $this->ALIGN . ' VALIGN=' . $this->VALIGN . '>';
	       	$ret .= $this->option[$i]->Display();
	       	$ret .= '</td>';
		}
	return $ret;
	}
	function ReturnDisplay()
	{
//Depreciated
	return $this->Display();
	}
}

class TableRow
{
	//This class will be a generic row within a table
	//Can hold multiple cells, but only 1 row
	var $cells = array();
	function TableRow()
	{
		//Constructor old style
		return $this->__constructor();
	}
	function __constructor()
	{
		//
	}
	function AddCell($cell)
	{
		$this->cells[] = $cell;
	}
	function SetEntry($item)
	{
		return $this->AddCell($item);
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		$ret = '<tr>';		
		foreach ($this->cells as $cell) 
		{
			if ($cell != NULL)
			{
		  		$ret .= $cell->Display();
			}
		}
		$ret .= '</tr>';
		return $ret;
	}
}

class TRow
{
	var $option;
	var $numoption;
	function TRow()
	{
		$this->numoption = 0;
	}
	function SetOption($newoption)
	{
		$this->numoption = $this->numoption + 1;
		$this->option[$this->numoption] = $newoption;
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		$ret = '<tr>';		
		for ($i = 1; $i <= $this->numoption; $i++)
		{
		  $ret .= $this->option[$i]->Display();
		}
		$ret .= '</tr>';
		return $ret;
	}
}
class TBody
{
	var $option;
	var $numoption;
	function TBody()
	{
		$this->numoption = 0;
	//	$row = new TRow();
	//	$this->SetOption($row);
	}
	function SetOption($newoption)
	{
		$this->numoption = $this->numoption + 1;
		$this->option[$this->numoption] = $newoption;
	}
	function Display()
	{
		return $this->ReturnDisplay();
	}
	function ReturnDisplay()
	{
		$ret = "";
		for ($i = 1; $i <= $this->numoption; $i++)
		{
		  $ret .= $this->option[$i]->ReturnDisplay();
		}
		return $ret;
	}
}
?>

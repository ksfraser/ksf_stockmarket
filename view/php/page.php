<?php

	require_once('form.php');
	require_once('table.php');
class Page
{
  var $content;
  var $numcontent;
  var $title = "PLEASE SET ME";
  var $header = "PLEASE SET ME";
  var $keywords;
  var $menu;
  var $buttons = array( "" => "");			
//  var $form;  FORM replaced by multiple contents

function Page($title, $header)
{
	$this->SetTitle($title);
	$this->SetHeader($header);
	$this->SetNumcontent(0);
	$this->menu = array( "Reload" => $_SERVER['PHP_SELF']);
}
function SetContent($content)
{
  $this->content[$this->numcontent] = $content;
  $this->IncNumcontent("1");
}
function SetNumcontent($content)
{
  $this->numcontent = $content;
}
function IncNumcontent($number = "1")
{
	$this->numcontent += $number;
}
function SetTitle($title)
{
  $this->title = $title;
}
function SetHeader($header)
{
	$this->header = $header;
}
function SetKeywords($keywords)
{
	$this->keywords = $keywords;
}
function SetMenu($newmenu)
{
  $this->menu = $newmenu;
}
function SetButtons($newbuttons)
{
  $this->buttons = $newbuttons;
}
function GetContent($number)
{
  return $this->content[$this->number];
}
function GetNumcontent()
{
  return $this->numcontent;
}
function GetTitle()
{
  return $this->title;
}
function GetHeader()
{
	return $this->header;
}
function GetKeywords()
{
	return $this->keywords;
}
function GetMenu()
{
  return $this->menu;
}
function GetButtons()
{
  return $this->buttons;
}


function Display()
{
//No longer will piecemeal echo to the page.  Will build then send.  This is to allow
//integration into TIKIWIKI as well.
  //echo "<html><head>";
  $ret = "<html><head>";
  $ret .= $this->DisplayTitle();
  $ret .= $this->DisplayStyles();
  //echo "</head><body>";
  $ret .= "</head><body>";
  $ret .= $this->DisplayHeader();
  $ret .= $this->DisplayMenu($this->menu);
  //$ret .= "<br />$this->numcontent";
  for ($i = 0; $i < $this->numcontent; $i++)
  {
	  //$ret .= "<br />Calling content [$i] <br />";
	$ret .= $this->content[$i]->Display();
	//$ret .= "<br />$this->numcontent - $i";
  }
  $ret .= $this->DisplayFooter();
  //echo "</body></html>";
  $ret .= "</body></html>";
  echo $ret;
  return $ret;

}

function EndDisplay()
{
//Depreciated - placed into display with change for multiple content
  $this->DisplayFooter();
  echo "</body></html>";

}

function DisplayTitle()
{
//  echo "<title> $this->title </title>";
  return "<title> $this->title </title>";
}
function DisplayStyles()
{
/* ?>
<style>
  a:link {color:green}
  a:visited {color:blue} 
  a:active {color:red}
</style>
<?
*/
return "<style>a:link {color:green} a:visited {color:blue} a:active {color:red}</style>";
}
function DisplayHeader()
{
  //echo "<h1> $this->header </h1>";
  return "<h1> $this->header </h1>";
}

function DisplayMenu($menu)
{
	$ret = "";
	if (!isset($menu))
	{
		return $ret;
	}
  //echo ('<table width = "100%" bgcolor = "white" cellpadding = "4" cellspacing = "4"><tr>');
  $ret .= '<table width = "100%" bgcolor = "white" cellpadding = "4" cellspacing = "4"><tr>';
  $width = 100/count($menu);
  while (list($name, $URL) = each($menu))
  {
    $ret .= $this->DisplayLinks($width, $name, $URL, $this->IsCurrentURL($URL) );
  }
  //echo "</tr>";
  //echo "</table>";
  $ret .= "</tr></table>";
  return $ret;
}
function IsCurrentURL($URL)
{
  /*
  if (strpos( $GLOBALS["SCRIPT_NAME"], $URL ) == false)
  {
    return false;
  }
  else
  {  
    return true;
  }
  */
  return false;
}

function DisplayLinks($width, $name, $URL, $current = false)
{
	$ret = "";
  if ($current)
  {
  //echo ('<td width="' . $width . '"><span class=menu>' . $name . '</span></td>');
	$ret .= '<td width="' . $width . '"><span class=menu>' . $name . '</span></td>';
  }
  else
  {
  //echo ('<td width = "' . $width . '"><a href="' . $URL . '"><span class=menu>' . $name . '</span></a></td>');
  $ret .= '<td width = "' . $width . '"><a href="' . $URL . '"><span class=menu>' . $name . '</span></a></td>';
  }
  return $ret;
}

function DisplayButtons()
{
	$ret = "";
	while (list($name, $URL) = each($this->buttons))
  	{
		//echo ('<form action="' . $URL . '" method="post"><input type="submit" name="' . $name . '" value="' . $name . '" /></form>');
		$ret .= '<form action="' . $URL . '" method="post"><input type="submit" name="' . $name . '" value="' . $name . '" /></form>';
	}
	return $ret;
}

function DisplayButtonGroup()
{
	$ret = '<table width="80%" cellpadding=2 cellspacing=0 bgcolor=#cccccc> <tr>';
	//echo('<table width="80%" cellpadding=2 cellspacing=0 bgcolor=#cccccc> <tr>');
	$width = 100/count($this->buttons);
	while (list($name, $URL) = each($this->buttons))
  	{
	/*	
		echo ('<form action="' . $URL . '" method="post">');
		echo ('<td align=center width=' . $width . '>');
		echo ('<input type="submit" name="' . $name . '" value="' . $name . '" />');
		echo ('</td></form>');
	*/
		$ret .= '<form action="' . $URL . '" method="post">';
		$ret .= '<td align=center width=' . $width . '>';
		$ret .= '<input type="submit" name="' . $name . '" value="' . $name . '" />';
		$ret .= '</td></form>';
	}
	//echo('</tr></table><br />');
	$ret .= '</tr></table><br />';
	return $ret;
}

function DisplayEntryForm()
{
//Depreciated since form isn't used anymore	
}


function DisplayFooter()
{
//depreciated
}
function DisplayBody()
{
//depreciated
}

}

?>

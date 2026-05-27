<?php 

class Textarea
{
	var $name;
	var $value;
	var $rows;
	var $columns;
	function Textarea($name, $value, $rows = 1, $columns = 32)
	{
		$this->SetName($name);
		$this->SetValue($value);
		$this->SetRows($rows);
		$this->SetColumns($columns);
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function SetValue($value)
	{
		$this->value = $value;
	}
	function SetRows($rows)
	{
		$this->rows = $rows;
	}
	function SetColumns($column)
	{
		$this->columns = $column;
	}
	function Display()
	{
		//echo ('<tr><TEXTAREA name="' . $this->name . '" ROWS=' . $this->rows. ' COLS=' . $this->columns . '>' . $this->value . '</TEXTAREA></tr>');	
		$ret ='<tr><TEXTAREA name="' . $this->name . '" ROWS=' . $this->rows. ' COLS=' . $this->columns . '>' . $this->value . '</TEXTAREA></tr>';
		return $ret;
	}
	function ReturnDisplay()
	{
		//Normally Display calls this function.
		//This is new, so there can't be legacy use
		//Designed to be part of a cell in a table, hence no tr/td wrappers
		//To use, pass to the constructor of a InputCell class.
		return '<TEXTAREA name="' . $this->name . '" ROWS=' . $this->rows. ' COLS=' . $this->columns . '>' . $this->value . '</TEXTAREA><';
	}
}

class Image
{
	var $name;
	var $src;
	function Image($name, $src)
	{
		$this->SetName($name);
		$this->SetValue($src);
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function SetValue($src)
	{
		$this->src = $src;
	}
	function Display()
	{
		//echo ('<input type=image name=' . $this->name . ' src="' . $this->src . '">');	
		$ret = '<input type=image name=' . $this->name . ' src="' . $this->src . '">';
		return $ret;
	}
	function ReturnDisplay()
	{
		//Normally Display calls this function.
		//This is new, so there can't be legacy use
		//Designed to be part of a cell in a table, hence no tr/td wrappers
		//To use, pass to the constructor of a InputCell class.
		return '<input type=image name=' . $this->name . ' src="' . $this->src . '">';
	}
}

class Password
{
	var $name;
	var $value;
	function Password()
	{
	}
	function Display()
	{
		//echo ('<tr><td>Name</td><td><input name=login></td></tr>');
	        //echo ('<tr><td>Password</td><td><input type=password name=passwd></td></tr>');
		$ret = '<tr><td>Name</td><td><input name=login></td></tr><tr><td>Password</td><td><input type=password name=passwd></td></tr>';
		return $ret;
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function SetPassword($password)
	{
		$this->value = $password;
	}
}

class Radio
{
	var $name;
	var $value;
	var $checked; //True or false
	function Radio($name, $value, $checked)
	{
		$this->SetName($name);
		$this->SetValue($value);
		$this->SetChecked($checked);
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function SetValue($value)
	{
		$this->value = $value;
	}
	function SetChecked($checked)
	{
		if ($checked = true)
		{
		  $this->checked = true;
	  	}
		else
		{
		  $this->checked = false;
		}
	}
	function Display()
	{
		if ($this->checked = true)
		{
			//echo ('<tr><td><input type=radio name=' . $this->name . ' value="' . $this->value . '" checked>' . $this->value . '</td></tr>');
			$ret = '<td><input type=radio name=' . $this->name . ' value="' . $this->value . '" checked>' . $this->value . '</td>';
		}
		else
		{	
			//echo ('<tr><td><input type=radio name=' . $this->name . ' value="' . $this->value . '">' . $this->value . '</td></tr>');	
			$ret = '<tr><td><input type=radio name=' . $this->name . ' value="' . $this->value . '">' . $this->value . '</td></tr>';
		}
		return $ret;
	}
	function ReturnDisplay()
	{
		//Normally Display calls this function.
		//This is new, so there can't be legacy use
		//Designed to be part of a cell in a table, hence no tr/td wrappers
		//To use, pass to the constructor of a InputCell class.
		if ($this->checked = true)
		{
			$ret = '<input type=radio name=' . $this->name . ' value="' . $this->value . '" checked>' . $this->value;
		}
		else
		{	
			$ret = '<input type=radio name=' . $this->name . ' value="' . $this->value . '">' . $this->value;
		}
		return $ret;
	
	}
}


class Checkbox
{
	var $name;
	var $value;
	var $checked; //True or false
	function Checkbox($name, $value, $checked)
	{
		$this->SetName($name);
		$this->SetValue($value);
		$this->SetChecked($checked);
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function SetValue($value)
	{
		$this->value = $value;
	}
	function SetChecked($checked)
	{
		if ($checked = true)
		{
		  $this->checked = true;
		}
		else
		{
		  $this->checked = false;
		}
	}
	function Display()
	{
		if ($this->checked = true)
		{
			//echo ('<tr><td><input type=checkbox name=' . $this->name . ' value="' . $this->value . '" checked>' . $this->value . '</td></tr>');
			$ret = '<tr><td><input type=checkbox name=' . $this->name . ' value="' . $this->value . '" checked>' . $this->value . '</td></tr>';
		}
		else
		{	
			//echo ('<tr><td><input type=checkbox name=' . $this->name . ' value="' . $this->value . '">' . $this->value . '</td></tr>');	
			$ret = '<tr><td><input type=checkbox name=' . $this->name . ' value="' . $this->value . '">' . $this->value . '</td></tr>';
		}
		return $ret;
	}
	function ReturnDisplay()
	{
		//Normally Display calls this function.
		//This is new, so there can't be legacy use
		//Designed to be part of a cell in a table, hence no tr/td wrappers
		//To use, pass to the constructor of a InputCell class.
		if ($this->checked = true)
		{
			$ret = '<input type=checkbox name=' . $this->name . ' value="' . $this->value . '" checked>' . $this->value;
		}
		else
		{	
			$ret = '<input type=checkbox name=' . $this->name . ' value="' . $this->value . '">' . $this->value;
		}
		return $ret;
	
	}
}

class Hidden
{
	var $name;
	var $value;
	function Hidden($name, $value)
	{
		$this->SetName($name);
		$this->SetValue($value);
	}
	function SetName($name)
	{
		$this->name = $name;
	}
	function SetValue($value)
	{
		$this->value = $value;
	}
	function Display()
	{
		//echo ('<input type=hidden name=' . $this->name . ' value="' . $this->value . '">');	
		$ret = '<input type=hidden name=' . $this->name . ' value="' . $this->value . '">';
		return $ret;
	}
	function ReturnDisplay()
	{
		return $this->Display();
	}
}

?>

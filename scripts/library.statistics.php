<?php

function standard_deviation_sample ($a)
{
  //variable and initializations
  $the_standard_deviation = 0.0;
  $the_variance = 0.0;
  $the_mean = 0.0;
  $the_array_sum = array_sum($a); //sum the elements
  $number_elements = count($a); //count the number of elements

  //calculate the mean
  $the_mean = $the_array_sum / $number_elements;

  //calculate the variance
  for ($i = 0; $i < $number_elements; $i++)
  {
    //sum the array
    $the_variance = $the_variance + ( ( $a[$i] - $the_mean) * ($a[$i] - $the_mean) );
  }

  $the_variance = $the_variance / ($number_elements - 1.0);

  //calculate the standard deviation
  $the_standard_deviation = pow( $the_variance, 0.5);

  //return the variance
  return $the_standard_deviation;
}

function variance_sample ($a)
{
  //variable and initializations
  $the_variance = 0.0;
  $the_mean = 0.0;
  $the_array_sum = array_sum($a); //sum the elements
  $number_elements = count($a); //count the number of elements

  //calculate the mean
  $the_mean = $the_array_sum / $number_elements;

  //calculate the variance
  for ($i = 0; $i < $number_elements; $i++)
  {
    //sum the array
    $the_variance = $the_variance + ($a[$i] - $the_mean) * ($a[$i] - $the_mean);
  }

  $the_variance = $the_variance / ($number_elements - 1.0);

  //return the variance
  return $the_variance;
}

function median ($a)
{
  //variable and initializations
  $the_median = 0.0;
  $index_1 = 0;
  $index_2 = 0;

  //sort the array
  sort($a);

  //count the number of elements
  $number_of_elements = count($a); 

  //determine if odd or even
  $odd = $number_of_elements % 2;

  //odd take the middle number
  if ($odd == 1)
  {
    //determine the middle
    $the_index_1 = $number_of_elements / 2;

    //cast to integer
    settype($the_index_1, "integer");

    //calculate the median 
    $the_median = $a[$the_index_1];
  }
  else
  {
    //determine the two middle numbers
    $the_index_1 = $number_of_elements / 2;
    $the_index_2 = $the_index_1 - 1;

    //calculate the median 
    $the_median = ($a[$the_index_1] + $a[$the_index_2]) / 2;
  }

  return $the_median;
}

function mean ($a)
{
  //variable and initializations
  $the_result = 0.0;
  $the_array_sum = array_sum($a); //sum the elements
  $number_of_elements = count($a); //count the number of elements

  //calculate the mean
  $the_result = $the_array_sum / $number_of_elements;

  //return the value
  return $the_result;
}

function binomial_coefficient ($n, $k)
{
  //variable and initializations
  $the_result = 0;
  $n_factorial = 0;
  $k_factorial = 0;
  $n_k_factorial = 0;

  //calculate n,k n-k factorial
  $n_factorial = factorial_integer($n);
  $k_factorial = factorial_integer($k);
  $n_k_factorial = factorial_integer($n - $k);

  if ($n_factorial != "error" and 
      $k_factorial != "error" and
      $n_k_factorial != "error")
  {
    $the_result = $n_factorial / ($k_factorial * $n_k_factorial);
  }
  else
  {
    return "error";
  }

  return $the_result;
}

function factorial_integer ($k)
{
  //variable and initializations
  $the_result = 1;

  //check to see if k is an integer
  if (!is_int($k))
  {
    return "error";
  }

  //check for k < 0
  if ($k < 0)
  {
    return "error";
  }

  //0! = 1
  if ($k == 0)
  {
    return 1;
  }

  //calculate the result
  for ($i = 2; $i <= $k; $i++)
  {
    $the_result = $the_result * $i;
  }

  //return the value
  return $the_result;
}



?>

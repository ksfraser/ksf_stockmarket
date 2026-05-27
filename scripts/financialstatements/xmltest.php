<?php

$string = "<?xml version='1.0'?>
<document>
<Revenue>
<t0>73.77</t0>
<t1>66.30</t1>
<t2>48.36</t2>
<t3>28.38</t3>
</Revenue>
</document>";

$xml = simplexml_load_string($string);

var_dump($xml);
?>

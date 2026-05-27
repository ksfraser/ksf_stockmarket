<?php

//Expect php __FILE__ arg1 arg2 ....
echo __FILE__ . "\n";
$filename = basename(__FILE__);

echo "Filename " . $filename   . " called as $argv[0]\n";
echo "Passed arguments:\n $argv[1] \t $argv[2] \t $argv[3] \t $argv[4] \n";

?>

#!/bin/sh

for x in `grep calc close-strategies.php|cut -f 2 -d ' ' `; 
do 
	echo " INSERT INTO codemeta.metadata_functions (idmetadata_functions, function_name, application, table_name, function_purpose, function_arguments, function_variables, function_body, returnvalue, returntype, codelanguage, rth_Component, rth_ReqNumber, usecase_who, usecase_when, usecase_what, usecase_why, author) VALUES (NULL, '$x', 'finance', 'transaction_close', 'Closing pricing points', '$symbol, $date', '', '', 'FALSE', 'bool', 'php', '', '', 'system', 'on insert of a transaction into transaction', 'calcuate the closing position values', 'so that checks can be made daily to advise that closing positions are hit', 'Kevin <fraser.ks@gmail.com>');" >> close.sql; 
done


#!/bin/sh
for ((i=1; i < "381"; i++)) 
do
	echo "insert into stockalert (idalerts, idstockinfo, username, value1, value2, runonce, runstatus) values ( '16', '$i', 'KEVIN', '20', '10', '0', '0' );" >> retract.sql
	echo "insert into stockalert (idalerts, idstockinfo, username, value1, value2, runonce, runstatus) values ( '17', '$i', 'KEVIN', '20', '10', '0', '0' );" >> retract.sql
	echo $i
done

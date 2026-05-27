#!/bin/sh

#$1 is app
#$2 is table

mysqldump -pm1l1ce $1 $2 > $2.sql
#vi $2.sql
rm -f sql-out.sql
cat $2.sql | awk '/^CREATE TABLE/, /;$/' > create.tables.sql
php ../skel-app/create2metadata.php
mysql -pm1l1ce < sql-out.sql
rm -f tasks.default.sql


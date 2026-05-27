#!/bin/sh
BASEDIR="/mnt/2/development/var/www/html/finance"

#Change to data directory
cd $BASEDIR/currentdata/prices

#Download files from Yahoo


#Process files from Yahoo into sql insert statements
for x in *csv; do 
	echo $x; 
	sleep 1;
	php $BASEDIR/scripts/prices/csv2sql.php $x && rm -f $x; 
done

#insert into MySQL
for x in *.sql; do 
	echo $x; 
	mysql -h defiant.silverdart.no-ip.org -u stockpriceinsert -p'stockpriceinsert' finance < $x && rm -f $x; 
done

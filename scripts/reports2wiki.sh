#!/bin/sh

#If you are going to run this, it makes sense to first build the most recent 
#candlestick and TA data as is available by running
#/scripts/candlestick/candlestick.sh


DATE=`date( 'Ymd' )`

cd /mnt/2/development/var/www/html/finance/wiki/maintenance

for x in `ls -d /mnt/2/development/var/www/html/finance/reports/*`; 
do 
	y=`echo $x|cut -f 10 -d '/'`;
	echo $y; 
	echo "=="$y"==" > $y.txt; 
	echo "==Candlestick==" >> $y.txt; 
	echo "[[Image:"$y".candlestick.png]]" >> $y.txt; 
	echo "==Heikanashi Candlestick==" >> $y.txt; 
	echo "[[Image:"$y".heikanashi.png]]" >> $y.txt; 

	php importTextFile.php --user=kevin2 --comment=$y' reports, technical analysis, candlesticks' --title='Stock symbol '$y' reports' $y.txt; 
	php importImages.php --user=kevin2 --overwrite --comment=$y' candlesticks' $x png; 
	rm -f $y.txt; 
done


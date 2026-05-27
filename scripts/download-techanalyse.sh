#!/bin/sh

cd /mnt/2/development/var/www/html/finance/scripts
php queryyahoo.php ; 
php queryyahoo-historical.php ; 
cd candlestick/; 
php checkcandlesticks.php; 
php fill_heikanashi.php;
cd ../technicalanalysis/; 
php technicalanalysis.php 
cd ../../reports
php gen.all.candlestick.php ;

#!/bin/sh

WD=/mnt/2/development/var/www/html/finance/scripts

php currentprice.php

cd $WD/bond
bond.sh

cd $WD/financialstatements
financialstatements.sh

#buffet is dependant upon 
#	the prices being up to date in stockinfo
#	recent bond rates
#	recent financial statements
cd $WD/buffet
buffet.sh


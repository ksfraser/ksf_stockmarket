#!/bin/sh

# This script is to download historical stock prices from Yahoo

#Download all prices for any stocks we don't already have anything for
#and then upload the resulting data into the database
echo "Running Getmissing"
php getmissing.php
./insertprices.sh

#Now get any data for the stocks in the database since the last
#time they have been downloaded
echo "Running Getnewest"
php getnewest.php
./insertprices.sh

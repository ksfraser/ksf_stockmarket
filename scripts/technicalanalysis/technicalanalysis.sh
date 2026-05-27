#!/bin/sh

#####These scripts assume checkcandlestick has already been run

#calculate the following:   
#	in calculatemovingaverages
#		movingaverage50
#		volume90
#		expmovingaverage90
#		movingaverage200
#		movingaverage260
#		volume260
#		standarddeviation260
#		expmovingaverage12
#		volume12
#		volume26
#		expmovingaverage26
#		momentumoscillator
#		priceoscillator
#		macd_histogram
#	in technicalanalysis proper
#		typicalprice
#		pricechangepercent
#		day_close
#		resistance12
#		support12
#		resistance26
#		support26
#		relativestrenghtindex
#		bollingerbandmiddle
#		bollingerbandupper
#		bollingerbandlower
#		bollingerpercentb
#		bollingerbandwidth
#		bollingerbandmiddle
#		bollingerbandupper
#		bollingerbandlower
#		bollingerpercentb
#		bollingerbandwidth
#		coefficientofvariation
php technicalanalysis.php



#calculate an indicator dependant on price and volume trends
#depends on 26, 90 and 260 day trends having been calculated
php volumealert.php

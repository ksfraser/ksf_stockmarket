<?php

//20090815 KF
//Volume as it indicates on trends

/*

According to DOW there were 3 trends
primary - 1+ years
secondary 1-3 months
tertiary up to 3 weeks

http://www.incademy.com/courses/Technical-analysis-I/Volume-data/6/1031/10002
For most technical analysts, volume is used as corroborative evidence of a trend rather than primary evidence. There are five basic rules:

   1. When prices are going up and the volume is increasing then the trend will stay in force and prices will continue to rise.

   2. When prices are going up and the volume is decreasing the trend is unlikely to continue and prices will either increase at a slower rate or start to fall.

   3. When prices are decreasing and volume is increasing then the trend will continue and prices will fall further.

   4. When prices are decreasing and the volume is also decreasing then the trend is unlikely to continue and the decline in prices will slow down or they will start to increase.

   5. When volume is consistent, not rising or falling, then the effect on prices is neutral and you need to find some other way of backing up your trend analysis.
*/

function ta_volumes( $data );
{
	//Requires an array of newest data first with at least 180 days data
	//to calculate the 90 day volume for 90 days worth.
	//
	//Going to use 12 day as close enough for 3 week
	//Using 90 day for 3 month
	//Not looking at primary trends here.
	$volume12 = movingaverage( $data, 12 );
	$volume26 = movingaverage( $data, 26 );
	$volume90 = movingaverage( $data, 90 );
	$count = count( $data );
	for( $i = 0; $i < $count; $i++)
	{
		$volume[$i]['volume12'] = $volume12[$i];
		$volume[$i]['volume26'] = $volume26[$i];
		$volume[$i]['volume90'] = $volume90[$i];
	}
	return $volume;
}


?>

<?php
require_once( 'HTML/QuickForm.php' );;

$form = new HTML_QuickForm('technicalanalysis');
$form->addElement('text', 'createddate', 'createddate: Record Created Date', array( 'size' => 11));
$form->addRule( 'createddate', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'createduser', 'createduser: Record Created by User', array( 'size' => 11));
$form->addRule( 'createduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateddate', 'updateddate: Record updated date', array( 'size' => 11));
$form->addRule( 'updateddate', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'updateduser', 'updateduser: Record Updated by user', array( 'size' => 11));
$form->addRule( 'updateduser', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'symbol', 'symbol: Stock Symbol', array( 'size' => 11));
$form->addRule( 'symbol', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'date', 'date: Date in stockprices', array( 'size' => 11));
$form->addRule( 'date', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'day_close', 'day_close: The daily closing price', array( 'size' => 11));
$form->addRule( 'day_close', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'typicalprice', 'typicalprice: The Typical Price is the high plus low plus close divided by 3', array( 'size' => 11));
$form->addRule( 'typicalprice', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'movingaverage50', 'movingaverage50: 50 Day Moving Average', array( 'size' => 11));
$form->addRule( 'movingaverage50', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'movingaverage200', 'movingaverage200: 200 Day Moving Average', array( 'size' => 11));
$form->addRule( 'movingaverage200', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'candlestick', 'candlestick: Candlestick Identified for this date', array( 'size' => 11));
$form->addRule( 'candlestick', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'expmovingaverage9', 'expmovingaverage9: 9 Day exponential Moving Average', array( 'size' => 11));
$form->addRule( 'expmovingaverage9', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'expmovingaverage12', 'expmovingaverage12: 12 Day exponential Moving Average', array( 'size' => 11));
$form->addRule( 'expmovingaverage12', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'expmovingaverage26', 'expmovingaverage26: 26 Day exponential Moving Average', array( 'size' => 11));
$form->addRule( 'expmovingaverage26', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'macd', 'macd: Moving Average ConvergenceDivergence describes the rate of changes in EMAs', array( 'size' => 11));
$form->addRule( 'macd', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'momentumoscillator', 'momentumoscillator: The Longer EMA subtracted from the shorter EMA usually 12 and 26', array( 'size' => 11));
$form->addRule( 'momentumoscillator', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'mamomentum', 'mamomentum: MACD momentum rising positive is bullish increasing', array( 'size' => 11));
$form->addRule( 'mamomentum', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'macrossover', 'macrossover: MA crossover True or False', array( 'size' => 11));
$form->addRule( 'macrossover', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'macenterlinecrossover', 'macenterlinecrossover: Is this a centerline crossover of the MA', array( 'size' => 11));
$form->addRule( 'macenterlinecrossover', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'priceoscillator', 'priceoscillator: Shows the percentage difference between 2 MAs 12 minus 26 div 26', array( 'size' => 11));
$form->addRule( 'priceoscillator', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'macd_histogram', 'macd_histogram: Difference between MACD and trigger line (ma9)', array( 'size' => 11));
$form->addRule( 'macd_histogram', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'linearregression', 'linearregression: Linear Regression', array( 'size' => 11));
$form->addRule( 'linearregression', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'linearregressionangle', 'linearregressionangle: Angle of Linear Regression', array( 'size' => 11));
$form->addRule( 'linearregressionangle', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'linearregressionslope', 'linearregressionslope: Slope of Linear Regression', array( 'size' => 11));
$form->addRule( 'linearregressionslope', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'linearregressionintercept', 'linearregressionintercept: Intercept of Linear Regression', array( 'size' => 11));
$form->addRule( 'linearregressionintercept', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'stochastic', 'stochastic: Stochastic Indicator', array( 'size' => 11));
$form->addRule( 'stochastic', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'relativestrenghtindex', 'relativestrenghtindex: Relative Strength Index', array( 'size' => 11));
$form->addRule( 'relativestrenghtindex', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'rsioscillator', 'rsioscillator: Relative Strength Oscillator is a leading indicator', array( 'size' => 11));
$form->addRule( 'rsioscillator', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'commoditychannelindex', 'commoditychannelindex: Commodity Channel Index', array( 'size' => 11));
$form->addRule( 'commoditychannelindex', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'pricechangepercent', 'pricechangepercent: The percentage change of the close price compared to yesterdays close price', array( 'size' => 11));
$form->addRule( 'pricechangepercent', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'volume12', 'volume12: Average Volume for the last 12 days', array( 'size' => 11));
$form->addRule( 'volume12', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'volume26', 'volume26: Average volume for the last 26 days', array( 'size' => 11));
$form->addRule( 'volume26', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'volume90', 'volume90: Average volume for the last 90 days', array( 'size' => 11));
$form->addRule( 'volume90', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'support12', 'support12: Support level last 12 days', array( 'size' => 11));
$form->addRule( 'support12', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'support26', 'support26: Support level last 26 days', array( 'size' => 11));
$form->addRule( 'support26', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'resistance12', 'resistance12: Resistance level last 12 days', array( 'size' => 11));
$form->addRule( 'resistance12', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'resistance26', 'resistance26: resistance level last 26 days', array( 'size' => 11));
$form->addRule( 'resistance26', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bollingerbandmiddle', 'bollingerbandmiddle: The middle bollinger band', array( 'size' => 11));
$form->addRule( 'bollingerbandmiddle', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bollingerbandupper', 'bollingerbandupper: The upper bollinger band', array( 'size' => 11));
$form->addRule( 'bollingerbandupper', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bollingerbandlower', 'bollingerbandlower: The lower bollinger band', array( 'size' => 11));
$form->addRule( 'bollingerbandlower', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bollingerpercentb', 'bollingerpercentb: The bollinger percent b indicator', array( 'size' => 11));
$form->addRule( 'bollingerpercentb', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'bollingerbandwidth', 'bollingerbandwidth: The bollinger bandwidth addresses the spread of the values', array( 'size' => 11));
$form->addRule( 'bollingerbandwidth', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'coefficientofvariation', 'coefficientofvariation: The coefficient of variation is 1/4 of the bandwidth', array( 'size' => 11));
$form->addRule( 'coefficientofvariation', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'movingaverage260', 'movingaverage260: Moving Average for 260 days (1 trading year)', array( 'size' => 11));
$form->addRule( 'movingaverage260', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'standarddeviation260', 'standarddeviation260: Standard Deviation 260 One trading year', array( 'size' => 11));
$form->addRule( 'standarddeviation260', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'annualreturn', 'annualreturn: The price appreciation in the last year', array( 'size' => 11));
$form->addRule( 'annualreturn', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'annualrisk', 'annualrisk: The annual risk standard dev divided by annual return', array( 'size' => 11));
$form->addRule( 'annualrisk', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'truerange', 'truerange:  MAX( High0-Low0, High0-Close1, Close1 - Low0 )', array( 'size' => 11));
$form->addRule( 'truerange', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'expmovingaverage90', 'expmovingaverage90: 90 day price EMA ', array( 'size' => 11));
$form->addRule( 'expmovingaverage90', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'voltrendind90', 'voltrendind90: 90 day Volume trend indicator', array( 'size' => 11));
$form->addRule( 'voltrendind90', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'voltrendind26', 'voltrendind26: 26 day Volume Trend indicator', array( 'size' => 11));
$form->addRule( 'voltrendind26', 'ERROR: Incorrect data type', 'alphanumeric');

$form->addElement('text', 'volume260', 'volume260: One years volume average', array( 'size' => 11));
$form->addRule( 'volume260', 'ERROR: Incorrect data type', 'numeric');

$form->addElement('text', 'voltrendind260', 'voltrendind260: Years volume trend indicator', array( 'size' => 11));
$form->addRule( 'voltrendind260', 'ERROR: Incorrect data type', 'alphanumeric');

$form->setDefaults( array(
	'createddate' => '',
	'createduser' => '',
	'updateddate' => '',
	'updateduser' => '',
	'symbol' => '',
	'date' => '',
	'day_close' => '',
	'typicalprice' => '',
	'movingaverage50' => '',
	'movingaverage200' => '',
	'candlestick' => '',
	'expmovingaverage9' => '',
	'expmovingaverage12' => '',
	'expmovingaverage26' => '',
	'macd' => '',
	'momentumoscillator' => '',
	'mamomentum' => '',
	'macrossover' => '',
	'macenterlinecrossover' => '',
	'priceoscillator' => '',
	'macd_histogram' => '',
	'linearregression' => '',
	'linearregressionangle' => '',
	'linearregressionslope' => '',
	'linearregressionintercept' => '',
	'stochastic' => '',
	'relativestrenghtindex' => '',
	'rsioscillator' => '',
	'commoditychannelindex' => '',
	'pricechangepercent' => '',
	'volume12' => '',
	'volume26' => '',
	'volume90' => '',
	'support12' => '',
	'support26' => '',
	'resistance12' => '',
	'resistance26' => '',
	'bollingerbandmiddle' => '',
	'bollingerbandupper' => '',
	'bollingerbandlower' => '',
	'bollingerpercentb' => '',
	'bollingerbandwidth' => '',
	'coefficientofvariation' => '',
	'movingaverage260' => '',
	'standarddeviation260' => '',
	'annualreturn' => '',
	'annualrisk' => '',
	'truerange' => '',
	'expmovingaverage90' => '',
	'voltrendind90' => '',
	'voltrendind26' => '',
	'volume260' => '',
	'voltrendind260' => '',
	)
);

$form->addElement('submit', null, 'Submit');

	if ( $form->validate() )
	{
		$form->freeze();
		//Now do something with the data
		require_once( 'data/generictable.php' );
		require_once( '../local.php' );
		Local_Init();
		include_once( '../model/technicalanalysis.class.php' );
		$technicalanalysis = new technicalanalysis();
		$technicalanalysis->Insert( $_POST );
	};

echo '<html><body>';
	$form->display();
echo '</body></html>';

?>
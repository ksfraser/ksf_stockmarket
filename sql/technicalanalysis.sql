DROP TABLE IF EXISTS `technicalanalysis`;
CREATE TABLE `technicalanalysis` (
`idtechnicalanalysis` int(11)   NULL auto_increment default '' comment 'Index',
`createddate` datetime(11)   NULL  default '' comment 'Record Created Date',
`createduser` int(11)   NULL  default '' comment 'Record Created by User',
`updateddate` timestamp(11)   NULL  default '' comment 'Record updated date',
`updateduser` int(11)   NULL  default '' comment 'Record Updated by user',
`symbol` varchar(11)   NULL  default '' comment 'Stock Symbol',
`date` date(11)   NULL  default '' comment 'Date in stockprices',
`day_close` float(11)   NULL  default '' comment 'The daily closing price',
`typicalprice` float(11)   NULL  default '' comment 'The Typical Price is the high plus low plus close divided by 3',
`movingaverage50` float(11)   NULL  default '' comment '50 Day Moving Average',
`movingaverage200` float(11)   NULL  default '' comment '200 Day Moving Average',
`candlestick` varchar(11)   NULL  default '' comment 'Candlestick Identified for this date',
`expmovingaverage9` float(11)   NULL  default '' comment '9 Day exponential Moving Average',
`expmovingaverage12` float(11)   NULL  default '' comment '12 Day exponential Moving Average',
`expmovingaverage26` float(11)   NULL  default '' comment '26 Day exponential Moving Average',
`macd` varchar(11)   NULL  default '' comment 'Moving Average ConvergenceDivergence describes the rate of changes in EMAs',
`momentumoscillator` float(11)   NULL  default '' comment 'The Longer EMA subtracted from the shorter EMA usually 12 and 26',
`mamomentum` float(11)   NULL  default '' comment 'MACD momentum rising positive is bullish increasing',
`macrossover` int(11)   NULL  default '' comment 'MA crossover True or False',
`macenterlinecrossover` int(11)   NULL  default '' comment 'Is this a centerline crossover of the MA',
`priceoscillator` float(11)   NULL  default '' comment 'Shows the percentage difference between 2 MAs 12 minus 26 div 26',
`macd_histogram` float(11)   NULL  default '' comment 'Difference between MACD and trigger line (ma9)',
`linearregression` float(11)   NULL  default '' comment 'Linear Regression',
`linearregressionangle` float(11)   NULL  default '' comment 'Angle of Linear Regression',
`linearregressionslope` float(11)   NULL  default '' comment 'Slope of Linear Regression',
`linearregressionintercept` float(11)   NULL  default '' comment 'Intercept of Linear Regression',
`stochastic` float(11)   NULL  default '' comment 'Stochastic Indicator',
`relativestrenghtindex` float(11)   NULL  default '' comment 'Relative Strength Index',
`rsioscillator` float(11)   NULL  default '' comment 'Relative Strength Oscillator is a leading indicator',
`commoditychannelindex` float(11)   NULL  default '' comment 'Commodity Channel Index',
`pricechangepercent` float(11)   NULL  default '' comment 'The percentage change of the close price compared to yesterdays close price',
`volume12` int(11)   NULL  default '' comment 'Average Volume for the last 12 days',
`volume26` int(11)   NULL  default '' comment 'Average volume for the last 26 days',
`volume90` int(11)   NULL  default '' comment 'Average volume for the last 90 days',
`support12` float(11)   NULL  default '' comment 'Support level last 12 days',
`support26` float(11)   NULL  default '' comment 'Support level last 26 days',
`resistance12` float(11)   NULL  default '' comment 'Resistance level last 12 days',
`resistance26` float(11)   NULL  default '' comment 'resistance level last 26 days',
`bollingerbandmiddle` float(11)   NULL  default '' comment 'The middle bollinger band',
`bollingerbandupper` float(11)   NULL  default '' comment 'The upper bollinger band',
`bollingerbandlower` float(11)   NULL  default '' comment 'The lower bollinger band',
`bollingerpercentb` float(11)   NULL  default '' comment 'The bollinger percent b indicator',
`bollingerbandwidth` float(11)   NULL  default '' comment 'The bollinger bandwidth addresses the spread of the values',
`coefficientofvariation` float(11)   NULL  default '' comment 'The coefficient of variation is 1/4 of the bandwidth',
`movingaverage260` float(11)   NULL  default '' comment 'Moving Average for 260 days (1 trading year)',
`standarddeviation260` float(11)   NULL  default '' comment 'Standard Deviation 260 One trading year',
`annualreturn` float(11)   NULL  default '' comment 'The price appreciation in the last year',
`annualrisk` float(11)   NULL  default '' comment 'The annual risk standard dev divided by annual return',
`truerange` float(11)   NULL  default '' comment ' MAX( High0-Low0, High0-Close1, Close1 - Low0 )',
`expmovingaverage90` float(11)   NULL  default '' comment '90 day price EMA ',
`voltrendind90` varchar(11)   NULL  default '' comment '90 day Volume trend indicator',
`voltrendind26` varchar(11)   NULL  default '' comment '26 day Volume Trend indicator',
`volume260` float(11)   NULL  default '' comment 'One years volume average',
`voltrendind260` varchar(11)   NULL  default '' comment 'Years volume trend indicator', PRIMARY KEY (`idtechnicalanalysis`)) ENGINE=InnoDB;

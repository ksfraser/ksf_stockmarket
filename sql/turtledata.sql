DROP TABLE IF EXISTS `turtledata`;
CREATE TABLE `turtledata` (
`idturtledata` int(11)   NULL  default '' comment 'Index of table',
`symbol` varchar(11)   NULL  default '' comment 'The stock symbol',
`date` date(11)   NULL  default '' comment 'The date this data is for',
`createddate` datetime(11)   NULL  default '' comment 'Date the record was created',
`createduser` int(11)   NULL  default '' comment 'Record created by user',
`updateddate` timestamp(11)   NULL  default '' comment 'date record was updated',
`updateduser` int(11)   NULL  default '' comment 'record updated by user',
`volatility` float(11)   NULL  default '' comment 'The volatility (N) of the market',
`unit` float(11)   NULL  default '' comment 'The unit size of the market',
`breakouthigh20` float(11)   NULL  default '' comment 'The 20 day high breakout value',
`breakoutlow20` float(11)   NULL  default '' comment 'The low 20 day breakout price',
`breakouthigh55` float(11)   NULL  default '' comment 'The high 55 day breakout price',
`breakoutlow55` float(11)   NULL  default '' comment 'The 55 day low breakout value',
`low10` float(11)   NULL  default '' comment 'The 10 day low for selling longs',
`high10` float(11)   NULL  default '' comment 'The 10 day high used for selling shorts',
`low20` float(11)   NULL  default '' comment 'The 20 day low price',
`high20` float(11)   NULL  default '' comment 'The 20 day high price',
`truerange` float(11)   NULL  default '' comment 'True range - MAX( High0-Low0, High0-Close1, Close1 - Low0 )',
`ignore20` int(11)   NULL  default '' comment 'Was the 20 day signal ignored due to the winning trade rule',
`positionadd` float(11)   NULL  default '' comment 'Once a breakout occurs, you can add to the position at 1/2N prices.  What is the next 1/2N price',
`sellallprice` float(11)   NULL  default '' comment 'All units are sold if the breakout20 is reached before the 10 day exit price',
`normalizedprice` float(11)   NULL  default '' comment 'Normalized price of the market - Current Price - 90day EMA divided by N', PRIMARY KEY (`symbol`, 'symbol', 'date')) ENGINE=InnoDB;

DROP TABLE IF EXISTS `hedgefolios`;
CREATE TABLE `hedgefolios` (
`idhedgefolios` int(11)   NULL auto_increment default '' comment 'The index of this table',
`idstockinfo` int(11)   NULL  default '' comment 'The Stock being evaluated',
`createddate` datetime(11)   NULL  default '' comment 'Time that this record was created',
`createduser` int(11)   NULL  default '' comment 'Record created by user',
`updateddate` timestamp(11)   NULL  default '' comment 'The time this record was updated',
`updateduser` int(11)   NULL  default '' comment 'Record updated by user',
`supportlevel` float(11)   NULL  default '' comment 'The technical indicator Support Level',
`resistancelevel` float(11)   NULL  default '' comment 'Technical indicator Resistance Level',
`Volume` float(11)   NULL  default '' comment 'Average trading volume',
`bollingerbands` varchar(11)   NULL  default '' comment 'The Bollinger Bands levels',
`elliotwave` varchar(11)   NULL  default '' comment 'The Elliot Wave values',
`fibonacci` varchar(11)   NULL  default '' comment 'Fibonacci indicators',
`sentiment` varchar(11)   NULL  default '' comment 'Sentiment Indicators',
`trailingpe` float(11)   NULL  default '' comment 'Trailing Price to Earnings',
`forwardpe` float(11)   NULL  default '' comment 'Forward Price to Earnings',
`pricetobook` float(11)   NULL  default '' comment 'Price to Book',
`pricetosale` float(11)   NULL  default '' comment 'Price to Sale',
`pricetocash` float(11)   NULL  default '' comment 'Price to Cash Flow',
`expectedgrowth` float(11)   NULL  default '' comment '5 years expected earnings growth',
`chartpattern` varchar(11)   NULL  default '' comment 'Chart Patterns',
`candlesticks` varchar(11)   NULL  default '' comment 'Candlesticks', PRIMARY KEY (`idhedgefolios`)) ENGINE=InnoDB;

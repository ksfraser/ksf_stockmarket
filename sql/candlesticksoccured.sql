DROP TABLE IF EXISTS `candlesticksoccured`;
CREATE TABLE `candlesticksoccured` (
`idcandlesticksoccured` int(11)   NULL auto_increment default '' comment 'Index',
`createddate` datetime(11)   NULL  default '' comment 'Record Created Date',
`createduser` int(11)   NULL  default '' comment 'Record Created by User',
`updateddate` timestamp(11)   NULL  default '' comment 'Record updated date',
`updateduser` int(11)   NULL  default '' comment 'Record Updated by user',
`symbol` varchar(11)   NULL  default '' comment 'Stock Symbol',
`date` date()   NULL  default '' comment 'Date in stockprices',
`candlestick` varchar(255)   NULL  default '' comment 'Candlestick Identified for this date', PRIMARY KEY (`idcandlesticksoccured`)) ENGINE=InnoDB;

DROP TABLE IF EXISTS `candlestickdates`;
CREATE TABLE `candlestickdates` (
`candlestickdates` date(11)   NULL  default '' comment 'The dates for which candlesticks have been calculated', PRIMARY KEY (`candlestickdates`)) ENGINE=InnoDB;

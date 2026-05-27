DROP TABLE IF EXISTS `stockexchange`;
CREATE TABLE `stockexchange` (
`idstockexchange` integer(8)   NOT NULL  default '' comment 'Stock Exchange index',
`exchange` varchar(45)   NOT NULL  default '' comment 'Exchange Name',
`YahooSymbol` varchar(45)   NOT NULL  default '' comment 'Yahoo Finance Symbol',
`GlobeInvestorSymbol` varchar(45)   NOT NULL  default '' comment 'Globe Investor Symbol', PRIMARY KEY (`idstockexchange`)) ENGINE=InnoDB;

DROP TABLE IF EXISTS `stockinfo`;
CREATE TABLE `stockinfo` (
`marketcap` float(11)   NULL  default '' comment 'The Market Capitalization',
`peratio` float(11)   NULL  default '' comment 'The PE Ratio',
`active` int(11)   NULL  default '' comment 'Is this symbol still active',
`cik` varchar(11)   NOT NULL  default '' comment 'CIK',
`idstockinfo` integer(8)   NOT NULL  default '' comment 'Index',
`idstocksector` int(11)   NOT NULL  default '' comment 'Stock Sector',
`createddate` timestamp(11)   NULL  default '' comment '',
`createduser` varchar(11)   NULL  default '' comment '',
`reviseddate` timestamp(11)   NULL  default '' comment '',
`reviseduser` varchar(11)   NULL  default '' comment '',
`dailychange` integer(10)   NOT NULL  default '' comment 'Price Change',
`stocksymbol` char(10)   NOT NULL  default '' comment 'Stock Symbol',
`corporatename` varchar(255)   NOT NULL  default '' comment 'Corporate Name',
`currentprice` float(8)   NOT NULL  default '' comment 'Last Trade Price',
`stockexchange` integer(4)   NOT NULL  default '' comment 'Stock Exchange',
`low` float(8)   NOT NULL  default '' comment 'Low',
`high` float(8)   NOT NULL  default '' comment 'High',
`yearlow` float(8)   NOT NULL  default '99999' comment '52 Week Low',
`yearhigh` float(8)   NOT NULL  default '' comment '52 Week High',
`averagevolume` integer(8)   NOT NULL  default '' comment 'Average Volume',
`dailyvolume` integer(11)   NOT NULL  default '-1' comment 'Daily Trading Volume',
`EPS` double(8)   NOT NULL  default '' comment 'Earnings Per Share',
`annualdividendpershare` float(8)   NOT NULL  default '0' comment 'Annual Dividend per Share',
`asofdate` date(16)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Last Update Date', PRIMARY KEY (`idstockinfo`)) ENGINE=InnoDB;

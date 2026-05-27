DROP TABLE IF EXISTS `dividends`;
CREATE TABLE `dividends` (
`iddividends` integer(8)   NOT NULL  default '0' comment 'Index',
`stocksymbol` varchar(8)   NOT NULL  default '' comment 'Stock',
`annualdividend` float(8)   NOT NULL  default '0.00' comment 'Annual Dividend',
`lastupdate` timestamp(16)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Last Update', PRIMARY KEY (`iddividends`)) ENGINE=InnoDB;

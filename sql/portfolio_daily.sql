DROP TABLE IF EXISTS `portfolio_daily`;
CREATE TABLE `portfolio_daily` (
`idportfolio_daily` int(11)   NULL auto_increment default '' comment 'Index',
`username` varchar(11)   NULL  default '' comment 'The user',
`tradedate` date(11)   NULL  default '' comment 'The date for this row of history',
`bookvalue` float(11)   NULL  default '' comment 'The book value of the portfolio on this date',
`marketvalue` float(11)   NULL  default '' comment 'The market value of the portfolio on this date',
`cash` float(11)   NULL  default '' comment 'Cash in the portfolio on this date',
`updateddate` date(11)   NULL  default '' comment 'The date this record was last updated',
`account` varchar(11)   NULL  default '' comment 'The account this record is for', PRIMARY KEY (`idportfolio_daily`)) ENGINE=InnoDB;

DROP TABLE IF EXISTS `evalfinancial`;
CREATE TABLE `evalfinancial` (
`summary` integer(11)   NOT NULL  default '-1' comment 'Summary (4)',
`idevalfinancial` int(11)   NULL  default '' comment 'Index',
`idstockinfo` int(11)   NULL  default '' comment 'Company',
`ownerearnings` float(10)   NULL  default '' comment 'Owners Earnings',
`roe` tinyint(1)   NULL  default '' comment 'Return on Equity',
`lasteval` timestamp(16)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Evaluation Time',
`user` varchar(45)   NOT NULL  default '' comment 'Evaluating User',
`retainearningsmv` tinyint(1)   NULL  default '' comment 'Retained Earnings become Market Value',
`debtratio` float(10)   NULL  default '' comment 'Debt to Equity Ratio',
`acceptabledebt` float(10)   NULL  default '' comment 'Acceptable Debt Level',
`lowcost` tinyint(1)   NULL  default '' comment 'Low Cost Operations', PRIMARY KEY (`idevalfinancial`)) ENGINE=InnoDB;

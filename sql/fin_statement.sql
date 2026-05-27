DROP TABLE IF EXISTS `fin_statement`;
CREATE TABLE `fin_statement` (
`dividendpershare1` float(11)   NULL  default '' comment 'dividendpershare last year',
`dividendpershare2` float(11)   NULL  default '' comment 'dividendpershare 2 years ago',
`dividendpershare3` float(11)   NULL  default '' comment 'dividendpershare 3 years ago',
`earningspershare1` float(11)   NULL  default '' comment 'earningspershare 1 year ago',
`earningspershare2` float(11)   NULL  default '' comment 'earningspershare 2 years ago',
`earningspershare3` float(11)   NULL  default '' comment 'earningspershare 3 years ago',
`idfin_statement` int(11)   NULL auto_increment default '' comment 'Table Index',
`idstockinfo` int(11)   NULL  default '' comment 'Stock',
`lasteval` timestamp(11)   NULL  default '' comment 'Last Evaluated',
`outstandingshares` int(10) unsigned  NULL  default '' comment 'Outstanding Common Shares',
`earningpershare` float(11)   NOT NULL  default '0' comment 'Earnings Per Share',
`symbol` varchar(6)   NOT NULL  default '' comment 'Stock Symbol',
`dividendpershare` float(11)   NOT NULL  default '0' comment 'Annual Dividend Per Share',
`ownerearnings` float(11)   NULL  default '' comment 'Owner Earnings',
`retainedearnings` float(11)   NOT NULL  default '0' comment 'Retained Earnings',
`netincome` float(11)   NULL  default '' comment 'Net Income',
`incomegrowth` float(11)   NULL  default '' comment 'Year over year Income Growth %',
`revenue` float(11)   NOT NULL  default '0' comment 'Revenue',
`revenuegrowth` float(11)   NOT NULL  default '' comment 'Revenue Growth Compared to 1 Year ago',
`revenuegrowth2` float(11)   NOT NULL  default '' comment 'Revenue Growth Compared to 2 Year ago',
`revenuegrowth3` float(11)   NOT NULL  default '' comment 'Revenue Growth Compared to 3 Year ago',
`totalasset` float(11)   NULL  default '' comment 'Total Assets',
`totalliability` float(11)   NULL  default '' comment 'Total Liabilities',
`totalequity` float(11)   NOT NULL  default '' comment 'Total Equity',
`totaldebt` float(11)   NOT NULL  default '' comment 'Total Debt',
`depletion` float(11)   NULL  default '' comment 'Depletion',
`amortization` float(11)   NULL  default '' comment 'Amortization',
`capitalexpenses` float(11)   NULL  default '' comment 'Capital Expenses',
`workingcapital` float(11)   NULL  default '' comment 'Change in Working Capital',
`user` varchar(45)   NULL  default '' comment 'Last Evaluation User', PRIMARY KEY (`idfin_statement`)) ENGINE=InnoDB;

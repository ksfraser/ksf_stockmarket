DROP TABLE IF EXISTS `quarter_statement`;
CREATE TABLE `quarter_statement` (
`idfin_statement` int(11)   NULL auto_increment default '' comment '',
`idstockinfo` int(11)   NULL  default '' comment '',
`netincome` float(11)   NULL  default '' comment '',
`depletion` float(11)   NULL  default '' comment '',
`amortization` float(11)   NULL  default '' comment '',
`capitalexpenses` float(11)   NULL  default '' comment '',
`workingcapital` float(11)   NULL  default '' comment '',
`lasteval` timestamp(11)   NULL  default '' comment '',
`user` varchar(11)   NULL  default '' comment '',
`outstandingshares` int(11) unsigned  NULL  default '' comment '',
`incomegrowth` float(11)   NULL  default '' comment 'Year over year Income Growth %',
`ownerearnings` float(11)   NULL  default '' comment '',
`totalasset` float(11)   NULL  default '' comment '',
`totalliability` float(11)   NULL  default '' comment '',
`totalequity` float(11)   NULL  default '' comment '',
`totaldebt` float(11)   NULL  default '' comment '',
`dividendpershare` float(11)   NULL  default '' comment '',
`earningpershare` float(11)   NULL  default '' comment 'Annual Earnings per share',
`revenue` float(11)   NULL  default '' comment 'Revenue from Income Statement',
`retainedearnings` float(11)   NULL  default '' comment 'Retained Earnings',
`revenuegrowth` float(11)   NULL  default '' comment 'Growth in revenue compared to previous year',
`revenuegrowth2` float(11)   NULL  default '' comment 'Revenue Growth compared to 2 years ago',
`revenuegrowth3` float(11)   NULL  default '' comment 'Revenue Growth compared to 3 years ago', PRIMARY KEY (`idfin_statement`)) ENGINE=InnoDB;

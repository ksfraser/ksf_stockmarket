DROP TABLE IF EXISTS `transaction`;
CREATE TABLE `transaction` (
`idusers` int(11)   NULL  default '' comment 'User',
`account` varchar(11)   NULL  default 'TRADE' comment 'Which account is this transaction in (TRADE/RRSP/TFSA) ',
`currency` varchar(11)   NULL  default 'CAD' comment 'Home Currency',
`foreigncurrency` varchar(11)   NULL  default 'CAD' comment 'Foreign Currency',
`idstockinfo` int(11)   NOT NULL  default '' comment 'Stock Information Index',
`transactiondate` date(10)   NOT NULL  default '' comment 'Transaction Date',
`createduser` int(10)   NOT NULL  default '' comment 'Created User',
`createddate` date(10)   NOT NULL  default '' comment 'Created Date',
`reviseduser` int(10)   NOT NULL  default '' comment 'Last Update User',
`reviseddate` date(10)   NOT NULL  default '' comment 'Last Update Date',
`sequence` integer(8)   NOT NULL  default '' comment 'Sequence',
`username` varchar(45)   NOT NULL  default '' comment 'User',
`stocksymbol` varchar(45)   NOT NULL  default '' comment 'Stock',
`numbershares` integer(8)   NOT NULL  default '0' comment 'Number',
`transactiontype` varchar(45)   NOT NULL  default '' comment 'Transaction Type',
`dollar` float(45)   NOT NULL  default '' comment 'Dollars', PRIMARY KEY (`sequence`)) ENGINE=InnoDB;

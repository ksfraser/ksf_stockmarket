DROP TABLE IF EXISTS `stock90highlow`;
CREATE TABLE `stock90highlow` (
`idstock90highlow` int(10)   NULL auto_increment default '' comment 'Index',
`stocksymbol` int(10) unsigned  NULL  default '' comment 'Stock Symbol',
`high` float(32)   NULL  default '' comment '',
`low` float(32)   NULL  default '' comment '',
`currentprice` float(32)   NULL  default '' comment '',
`idstockinfo` int(10) unsigned  NULL  default '' comment '',
`createddate` timestamp(32)   NULL  default '' comment '',
`createduser` varchar(45)   NULL  default '' comment '',
`reviseddate` timestamp(32)   NULL  default '' comment '',
`reviseduser` varchar(45)   NULL  default '' comment '',
`active` int(1)   NULL  default '' comment 'Is this symbol still active',
`cik` varchar(11)   NULL  default '' comment 'SEC's CIK value for the company',
`KEY` `active_index`(32)   NOT NULL  default '' comment '', PRIMARY KEY (`idstock90highlow`)) ENGINE=InnoDB;

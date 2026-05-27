CREATE TABLE `dividendpayment` (
  `iddividendpayment` int(10) unsigned NOT NULL auto_increment COMMENT 'Index',
  `stocksymbol` varchar(45) NOT NULL default '',
  `dividendpershare` float NOT NULL default '0' COMMENT 'Dividend Per Share',
  `lastupdate` timestamp NOT NULL default CURRENT_TIMESTAMP COMMENT 'Last Updated',
  `idstockexchange` int(11) NOT NULL COMMENT 'The Exchange the stock is on',
  `exdividenddate` date NOT NULL COMMENT 'The date the owner of record for the stock is used to pay the dividend',
  `idstockinfo` int(11) NOT NULL COMMENT 'The Stockinfo Index',
  PRIMARY KEY  (`iddividendpayment`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

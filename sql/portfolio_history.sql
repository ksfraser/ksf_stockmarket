DROP TABLE IF EXISTS `portfolio_history`;
CREATE TABLE `portfolio_history` (
`stocksymbol` varchar(10)   NULL  default '' comment '',
`username` varchar(45)   NOT NULL  default '' comment '',
`numbershares` double(10)   NULL  default '' comment '',
`bookvalue` float(10)   NULL  default '' comment '',
`marketvalue` float(10)   NULL  default '' comment '',
`currentprice` float(10)   NULL  default '' comment '',
`profitloss` float(10)   NULL  default '' comment '',
`marketbook` float(10)   NULL  default '' comment '',
`annualdividendpershare` float(10)   NULL  default '' comment '',
`dividendpercentbookvalue` float(10)   NULL  default '' comment '',
`dividendpercentmarketvalue` float(10)   NULL  default '' comment '',
`lastupdate` timestamp(17)   NULL  default '' comment '',
`dividendyield` float(10)   NULL  default '' comment '',
`percenttotalbookvalue` float(10)   NULL  default '' comment '',
`percenttotalmarketvalue` float(10)   NULL  default '' comment '',
`percenttotaldividend` float(10)   NULL  default '' comment '',
`idportfolio_history` int(10) unsigned  NULL auto_increment default '' comment '',
`yield` float(10)   NULL  default '' comment '',
`annualdividend` float(10)   NULL  default '' comment '',
`dividendbookvalue` float(10)   NULL  default '' comment '', PRIMARY KEY (`idportfolio_history`)) ENGINE=InnoDB;

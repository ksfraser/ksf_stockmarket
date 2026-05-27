DROP TABLE IF EXISTS `portfolio`;
CREATE TABLE `portfolio` (
`idportfolio` integer(8)   NOT NULL  default '' comment 'Index',
`username` varchar(45)   NOT NULL  default '' comment 'User',
`account` varchar(45)   NOT NULL  default 'ALL' comment 'Account',
`stocksymbol` varchar(7)   NOT NULL  default '' comment 'Stock',
`numbershares` float(8)   NOT NULL  default '0' comment 'Number of Shares Owned',
`bookvalue` float(8)   NOT NULL  default '0' comment 'Book Value',
`dividendbookvalue` float(11)   NOT NULL  default '' comment 'Dividend Adjusted Book Value',
`marketvalue` float(8)   NOT NULL  default '0' comment 'Market Value',
`profitloss` float(8)   NOT NULL  default '0' comment 'Profit or Loss',
`marketbook` float(8)   NOT NULL  default '0' comment 'Market Value to Book Value',
`yield` integer(8)   NOT NULL  default '' comment 'Price Yield',
`currentprice` float(8)   NOT NULL  default '0' comment 'Current Price',
`annualdividendpershare` integer(8)   NOT NULL  default '0' comment 'Annual Dividend per Share',
`annualdividend` float(8)   NOT NULL  default '' comment 'Annual Dividend',
`dividendpercentbookvalue` float(8)   NOT NULL  default '0' comment 'Dividend Percent of Book Value',
`dividendpercentmarketvalue` float(8)   NOT NULL  default '0' comment 'Dividend Percent of Market Value',
`dividendyield` float(8)   NOT NULL  default '' comment 'Dividend Yield',
`percenttotalmarketvalue` float(8)   NOT NULL  default '' comment 'MV Percentage of Portfolio Market Value',
`percenttotalbookvalue` float(8)   NOT NULL  default '' comment 'BV Percentage of Portfolio Book Value',
`percenttotaldividend` float(8)   NOT NULL  default '' comment 'Div Percentage of Portfolio Dividend Value',
`lastupdate` timestamp(16)   NOT NULL  default '' comment 'Last Update', PRIMARY KEY (`idportfolio`)) ENGINE=InnoDB;

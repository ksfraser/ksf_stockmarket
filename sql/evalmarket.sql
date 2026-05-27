DROP TABLE IF EXISTS `evalmarket`;
CREATE TABLE `evalmarket` (
`netvalue` float(11)   NOT NULL  default '0' comment 'The Assets - Liabilities from the financial Statement',
`idevalmarket` int(11)   NULL  default '' comment 'Index',
`idstockinfo` int(11)   NULL  default '' comment 'Company',
`ownerearnings` float(10)   NULL  default '' comment 'Owners Earnings',
`discountrate` int(11)   NULL  default '10' comment 'Discount Rate (Risk Free Rate - 30Yr bond + 3%)',
`incomegrowth` int(11)   NULL  default '' comment 'year over year growth percentage',
`value` int(11)   NULL  default '' comment 'Value of Business',
`netincome` float(10)   NULL  default '' comment 'Net Income',
`depreciation` float(10)   NULL  default '' comment 'Depreciation',
`depletion` float(10)   NULL  default '' comment 'Depletion',
`amortization` float(10)   NULL  default '' comment 'Amortization',
`capitalexpenses` float(10)   NULL  default '' comment 'Capital Expense',
`workingcapital` float(10)   NULL  default '' comment 'Working Capital',
`marketcap` bigint(19)   NULL  default '' comment 'Market Capitalization',
`marginsafety` float(10)   NULL  default '' comment 'Percent Margin of Safety',
`lasteval` timestamp(16)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Evaluation Time',
`user` varchar(45)   NOT NULL  default '' comment 'Evaluating User',
`outstandingshares` integer(10)   NOT NULL  default '' comment 'Number of Outstanding Shares', PRIMARY KEY (`idevalmarket`)) ENGINE=InnoDB;

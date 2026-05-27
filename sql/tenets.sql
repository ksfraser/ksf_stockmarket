DROP TABLE IF EXISTS `tenets`;
CREATE TABLE `tenets` (
`idtenets` int(8)   NOT NULL  default '' comment 'Index',
`stocksymbol` char(7)   NOT NULL  default 'ABCD' comment 'Company',
`simple` integer(45)   NOT NULL  default '' comment 'Simple Business',
`consistent` integer(45)   NOT NULL  default '' comment 'Consistent Performance',
`longterm` integer(45)   NOT NULL  default '' comment 'Long Term Prospects',
`rationalmanager` integer(45)   NOT NULL  default '' comment 'Rational Management',
`candid` integer(45)   NOT NULL  default '' comment 'Candid with Shareholders',
`resistinstitution` integer(45)   NOT NULL  default '' comment 'Management resists the Institution',
`focusroe` integer(45)   NOT NULL  default '' comment 'Focus on Return on Equity, not EPS',
`ownerearnings` integer(45)   NOT NULL  default '' comment 'Calculated Owner Earnings',
`highprofitmargin` integer(45)   NOT NULL  default '' comment 'High Profit Margins',
`retainedtomarket` integer(45)   NOT NULL  default '' comment 'Retained Earnings become Market Value',
`valueofbusiness` integer(45)   NOT NULL  default '' comment 'Value of Business',
`discounted` integer(45)   NOT NULL  default '' comment 'Purchase at Discount', PRIMARY KEY (`idtenets`)) ENGINE=InnoDB;

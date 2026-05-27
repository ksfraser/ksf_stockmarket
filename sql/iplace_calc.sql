DROP TABLE IF EXISTS `iplace_calc`;
CREATE TABLE `iplace_calc` (
`iplace_calc` int(11)   NULL auto_increment default '' comment 'Index',
`earningsgrowth` tinyint(1)   NULL  default '' comment 'Are earnings growing',
`earningsaccel` tinyint(1)   NULL  default '' comment 'Are earnings growth accelerating',
`pe` float(11)   NULL  default '' comment 'Price to Earnings ratio',
`tradingvolume` int(11)   NULL  default '' comment 'Trading Volume',
`institutioninterest` int(11)   NULL  default '' comment 'Percentage of shares owned by institutions',
`orderimbalance` tinyint(1)   NULL  default '' comment 'Balance of buy and sell orders',
`shortinterest` tinyint(1)   NULL  default '' comment 'Is there a lot of short options sold',
`volatility` float(11)   NULL  default '' comment 'The volatility of the share',
`createduser` int(11)   NULL  default '' comment 'Created By User',
`createddate` datetime(11)   NULL  default '' comment 'Created Date',
`updateduser` int(11)   NULL  default '' comment 'Updated by User',
`updateddate` timestamp(11)   NULL  default '' comment 'Updated Date',
`idstockinfo` int(11)   NULL  default '' comment 'Company',
`dividendearningratio` float(11)   NULL  default '' comment 'Dividends per share divided by earnings per share',
`extracash` tinyint(1)   NULL  default '' comment 'Does the company have cash on hand',
`shareholderprofitgoal` tinyint(1)   NULL  default '' comment 'Management focused on shareholder profit',
`dividendincreases` tinyint(1)   NULL  default '' comment 'Track record of dividend increases',
`score` int(11)   NULL  default '' comment 'Score of this filter', PRIMARY KEY (`iplace_calc`)) ENGINE=InnoDB;

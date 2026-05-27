DROP TABLE IF EXISTS `investorplace`;
CREATE TABLE `investorplace` (
`idinvestorplace` int(11)   NULL auto_increment default '' comment 'Index',
`seventyfivepercent` tinyint(1)   NULL  default '' comment 'Does the company depend on 75 percent or greater of domestic sales',
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
`newproductline` tinyint(1)   NULL  default '' comment 'Innovations - new products that are needed',
`restructuring` tinyint(1)   NULL  default '' comment 'Is the company cutting costs by restructuring',
`reengineering` tinyint(1)   NULL  default '' comment 'Is the company reengineering themselves',
`sharebuyback` tinyint(1)   NULL  default '' comment 'Share Buy Back',
`headcountcuts` tinyint(1)   NULL  default '' comment 'Announced staff reductions',
`spinoffs` tinyint(1)   NULL  default '' comment 'Shedding lines of business as spin-offs',
`reducedrd` tinyint(1)   NULL  default '' comment 'Reducing research and development',
`extracash` tinyint(1)   NULL  default '' comment 'Does the company have cash on hand',
`shareholderprofitgoal` tinyint(1)   NULL  default '' comment 'Management focused on shareholder profit',
`dividendincreases` tinyint(1)   NULL  default '' comment 'Track record of dividend increases',
`score` int(11)   NULL  default '' comment 'Score of this filter', PRIMARY KEY (`idinvestorplace`)) ENGINE=InnoDB;

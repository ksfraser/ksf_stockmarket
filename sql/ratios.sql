DROP TABLE IF EXISTS `ratios`;
CREATE TABLE `ratios` (
`attractivesum` int(11)   NULL  default '' comment 'Sum of Attractive Scores',
`attractiveroa` int(11)   NULL  default '' comment 'Is the ROA attractive',
`attractiveroce` int(11)   NULL  default '' comment 'is the ROCE attractive',
`attractivegross` int(11)   NULL  default '' comment 'is the Gross Margin attractive',
`attractivepretax` int(11)   NULL  default '' comment 'Is the PreTax margin attractive',
`attractivenet` int(11)   NULL  default '' comment 'Is the Net Margin attractive',
`sustaindebtratio` int(11)   NULL  default '' comment 'Is the debt ratio covered by income long term',
`idratios` int(11)   NULL auto_increment default '' comment 'Index',
`idstockinfo` int(11)   NULL  default '' comment 'Stock',
`roeattractive` int(11)   NULL  default '' comment 'Is the ROE attractive (> 15%)',
`lowcost` int(11)   NULL  default '' comment 'Low Cost operations (opmargin > .1 )',
`createddate` datetime(11)   NULL  default '' comment 'Created Timestamp',
`debtratio` float(11)   NULL  default '' comment 'Debt Ratio (debt/assets)',
`acceptabledebtratio` float(11)   NULL  default '' comment 'Acceptable Debt Ratio (Net Income/Revenue)',
`roe` float(11)   NULL  default '' comment 'Return On Equity (Net Income/ Total Equity)',
`roa` float(11)   NULL  default '' comment 'Return On Assets (Net Income / Total Assets)',
`operatingmargin` float(11)   NULL  default '' comment 'Operating Margin (Operating Income / Revenue )',
`roce` float(11)   NULL  default '' comment 'Return on Capital Employed (Net Income / Debt + equity)',
`grossprofitmargin` float(11)   NULL  default '' comment 'Gross Profit Margin (Gross Profit/Revenue)',
`pretaxmargin` float(11)   NULL  default '' comment 'PreTax Margin (pretax income/revenue)',
`netmargin` float(11)   NULL  default '' comment 'Net Margin (Net Income / Revenue )',
`updateddate` timestamp(11)   NULL  default '' comment 'Updated Timestamp',
`createduser` int(11)   NULL  default '' comment 'Created by User',
`updateduser` int(11)   NULL  default '' comment 'Updated by User',
`peratio` float(11)   NULL  default '' comment 'Price to Earnings Ratio', PRIMARY KEY (`idratios`)) ENGINE=InnoDB;

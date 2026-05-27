DROP TABLE IF EXISTS `evalsummary`;
CREATE TABLE `evalsummary` (
`idstockinfo` varchar(6)   NOT NULL  default '' comment 'Stock Symbol',
`totalscore` integer(11)   NOT NULL  default '-1' comment 'Total of Scores (36)',
`reviseddate` TIMESTAMP(17)   NOT NULL  default '' comment 'Last Revision Date',
`marginsafety` float(11)   NOT NULL  default '-999999' comment 'Margin of Safety (%)',
`ratioscore` int(11)   NULL  default '' comment 'Score from Ratios table (8)',
`iplacecalcscore` int(11)   NULL  default '' comment 'Score from iplace_calc (10)',
`managementscore` integer(11)   NOT NULL  default '-1' comment 'Management Tenets score (9)',
`financialscore` integer(11)   NOT NULL  default '-1' comment 'Financial Tenets score (4)',
`businessscore` integer(11)   NOT NULL  default '-1' comment 'Business Tenets score (5)',
`reviseduser` VARCHAR(45)   NOT NULL  default '' comment 'Revised by User', PRIMARY KEY (`idstockinfo`)) ENGINE=InnoDB;

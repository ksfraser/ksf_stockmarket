DROP TABLE IF EXISTS `evalbusiness`;
CREATE TABLE `evalbusiness` (
`idevalbusiness` int(11)   NULL  default '' comment 'Index',
`idstockinfo` int(11)   NULL  default '' comment 'Company',
`lasteval` timestamp(16)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Evaluation Time',
`user` varchar(45)   NOT NULL  default '' comment 'Evaluating User',
`summary` int(11)   NOT NULL  default '' comment 'Summary (5)',
`simple` tinyint(1)   NULL  default '' comment 'Simple Business',
`cosnsistanthistory` tinyint(1)   NULL  default '' comment 'Consistent Performance',
`neededproduct` tinyint(1)   NULL  default '' comment 'Needed Product',
`noclosesubstitute` tinyint(1)   NULL  default '' comment 'No close substitute of Product',
`regulated` tinyint(1)   NULL  default '' comment 'Regulated Industry', PRIMARY KEY (`idevalbusiness`)) ENGINE=InnoDB;

DROP TABLE IF EXISTS `evalmanagement`;
CREATE TABLE `evalmanagement` (
`idevalmanagement` int(11)   NULL  default '' comment 'Index',
`idstockinfo` int(11)   NULL  default '' comment 'Corporation',
`managementowners` tinyint(1)   NULL  default '' comment 'Management are shareholders',
`benefitreinvest` tinyint(1)   NULL  default '' comment 'Beneficial Reinvestment of Earnings',
`expandbypurchase` tinyint(1)   NULL  default '' comment 'Expands the business through acquisitions',
`mimiccompetition` tinyint(1)   NULL  default '' comment 'Management mimics the compeition (Lemmings)',
`hyperactivity` tinyint(1)   NULL  default '' comment 'Hyperactive Management',
`cosnsistanthistory` tinyint(1)   NULL  default '' comment 'Consistent Operating History (Predictability)',
`communicatemorethangaap` tinyint(1)   NULL  default '' comment 'Management Communicates more than just GAAP',
`publicconfession` tinyint(1)   NULL  default '' comment 'Confesses errors in public',
`lasteval` timestamp(16)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Evaluation Time',
`frfeqreorg` tinyint(1)   NULL  default '' comment 'Frequent Re-orgs and Cost Cutting announcements',
`user` varchar(45)   NOT NULL  default '' comment 'Evaluating User',
`summary` int(10)   NOT NULL  default '' comment 'Summary Total ( 9 )', PRIMARY KEY (`idevalmanagement`)) ENGINE=InnoDB;

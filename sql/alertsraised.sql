DROP TABLE IF EXISTS `alertsraised`;
CREATE TABLE `alertsraised` (
`idalertsraised` integer(10)   NOT NULL  default '' comment 'Index',
`username` varchar(45)   NOT NULL  default '' comment 'User',
`idalerts` integer(10)   NOT NULL  default '' comment 'Alert Index',
`cleared` tinyint(1)   NOT NULL  default '0' comment 'Cleared Flag',
`lastupdate` timestamp(17)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Last Updated',
`raisedtimestamp` timestamp(17)   NOT NULL  default 'CURRENT_TIMESTAMP' comment 'Alert Raised',
`idstockalert` integer(10)   NOT NULL  default '' comment 'Stockalert Index', PRIMARY KEY (`idalertsraised`)) ENGINE=InnoDB;

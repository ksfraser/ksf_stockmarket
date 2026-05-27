DROP TABLE IF EXISTS `stockalert`;
CREATE TABLE `stockalert` (
`idstockalert` int(8)   NOT NULL  default '' comment 'Index',
`idalerts` int(8)   NOT NULL  default '' comment 'Alert',
`idstockinfo` int(8)   NOT NULL  default '' comment 'Stock Symbol',
`username` varchar(45)   NOT NULL  default '' comment 'User',
`value1` varchar(45)   NOT NULL  default '' comment 'First Criteria',
`value2` varchar(45)   NOT NULL  default '' comment 'Second Criteria',
`runonce` int(1)   NOT NULL  default '0' comment 'Run Once',
`runstatus` int(1)   NOT NULL  default '0' comment 'Run Status', PRIMARY KEY (`idstockalert`)) ENGINE=InnoDB;

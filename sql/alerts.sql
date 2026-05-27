DROP TABLE IF EXISTS `alerts`;
CREATE TABLE `alerts` (
`idalerts` int(8)   NOT NULL  default '' comment 'index',
`alertdescription` varchar(45)   NOT NULL  default '' comment 'Description',
`alertfunctionname` varchar(45)   NOT NULL  default '' comment 'Called Function',
`expirydate` date(11)   NULL  default '' comment 'Expiry Date of Alert', PRIMARY KEY (`idalerts`)) ENGINE=InnoDB;

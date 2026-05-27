DROP TABLE IF EXISTS `cash`;
CREATE TABLE `cash` (
`name` varchar(11)   NULL  default '' comment '',
`value` float(11)   NOT NULL  default '' comment '',
`currency` varchar(11)   NOT NULL  default '' comment '',
`type` varchar(11)   NOT NULL  default '' comment '',
`owner` varchar(11)   NOT NULL  default '' comment '',
`cost` float(11)   NOT NULL  default '' comment '',
`date` date(11)   NOT NULL  default '' comment '', PRIMARY KEY ()) ENGINE=InnoDB;

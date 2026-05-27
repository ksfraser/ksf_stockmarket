DROP TABLE IF EXISTS `stockprices`;
CREATE TABLE `stockprices` (
`adjustedclose` float(11)   NOT NULL  default '' comment 'Split Adjusted Close Price',
`symbol` varchar(11)   NULL  default '' comment '',
`date` date(11)   NOT NULL  default '' comment '',
`previous_close` float(11)   NOT NULL  default '' comment '',
`day_open` float(11)   NOT NULL  default '' comment '',
`day_low` float(11)   NOT NULL  default '' comment '',
`day_high` float(11)   NOT NULL  default '' comment '',
`day_close` float(11)   NOT NULL  default '' comment '',
`day_change` float(11)   NOT NULL  default '' comment '',
`bid` float(11)   NOT NULL  default '' comment '',
`ask` float(11)   NOT NULL  default '' comment '',
`volume` int(11)   NOT NULL  default '' comment '', PRIMARY KEY ()) ENGINE=InnoDB;

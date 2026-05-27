DROP TABLE IF EXISTS `fxprices`;
CREATE TABLE `fxprices` (
`currency` varchar(11)   NULL  default '' comment '',
`date` date(11)   NOT NULL  default '' comment '',
`previous_close` float(11)   NOT NULL  default '' comment '',
`day_open` float(11)   NOT NULL  default '' comment '',
`day_low` float(11)   NOT NULL  default '' comment '',
`day_high` float(11)   NOT NULL  default '' comment '',
`day_close` float(11)   NOT NULL  default '' comment '',
`day_change` float(11)   NOT NULL  default '' comment '',
`foreigncurrency` varchar(11)   NOT NULL  default '0' comment 'Foreign Currency', PRIMARY KEY ()) ENGINE=InnoDB;

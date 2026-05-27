DROP TABLE IF EXISTS `heikanashi`;
CREATE TABLE `heikanashi` (
`symbol` varchar(11)   NULL  default '' comment 'The symbol',
`date` date(11)   NULL  default '' comment 'The date of the record',
`day_open` float(11)   NULL  default '' comment 'The Heiken Ashi Day Open value',
`day_close` float(11)   NULL  default '' comment 'The Heiken Ashi Day Close value',
`day_high` float(11)   NULL  default '' comment 'The Heiken Ashi Day High value',
`day_low` float(11)   NULL  default '' comment 'The Heiken Ashi Day Low value', PRIMARY KEY (`symbol`, 'symbol', 'date')) ENGINE=InnoDB;

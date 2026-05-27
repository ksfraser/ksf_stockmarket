DROP TABLE IF EXISTS `candlestickactions`;
CREATE TABLE `candlestickactions` (
`candlestick_name` varchar(32)   NULL  default '' comment 'The name of the candlestick',
`candlestick_name11` varchar(11)   NULL  default '' comment 'The name trimmed to 11 chars as that happened in some tables',
`candlestick_detail` varchar(255)   NULL  default '' comment 'Details on the meaning of the candlestick',
`candlestick_action` varchar(32)   NULL  default '' comment 'What action to take because of this candlestick',
`candlestick_action_value` int(11)   NOT NULL  default '50' comment 'Action Strength value', PRIMARY KEY ()) ENGINE=InnoDB;

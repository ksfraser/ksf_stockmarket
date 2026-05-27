CREATE TABLE `candlestickactions` (
  `candlestick_name` varchar(32) NOT NULL COMMENT 'The name of the candlestick',
  `candlestick_name11` varchar(11) NOT NULL COMMENT 'The name trimmed to 11 chars as that happened in some tables',
  `candlestick_detail` varchar(255) NOT NULL COMMENT 'Details on the meaning of the candlestick',
  `candlestick_action` varchar(32) NOT NULL COMMENT 'What action to take because of this candlestick',
  UNIQUE KEY `Name` (`candlestick_name`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

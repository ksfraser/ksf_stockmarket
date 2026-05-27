CREATE TABLE `fin_statement` (
  `dividendpershare1` float NOT NULL default '0' COMMENT 'dividendpershare last year',
  `dividendpershare2` float NOT NULL default '0' COMMENT 'dividendpershare 2 years ago',
  `dividendpershare3` float NOT NULL default '0' COMMENT 'dividendpershare 3 years ago',
  `earningspershare1` float NOT NULL default '0' COMMENT 'earningspershare 1 year ago',
  `earningspershare2` float NOT NULL default '0' COMMENT 'earningspershare 2 years ago',
  `earningspershare3` float NOT NULL default '0' COMMENT 'earningspershare 3 years ago',
  PRIMARY KEY  (`idfin_statement`)
) ENGINE=MyISAM AUTO_INCREMENT=2509 DEFAULT CHARSET=latin1;


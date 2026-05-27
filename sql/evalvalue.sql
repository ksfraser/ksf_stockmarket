DROP TABLE IF EXISTS `evalvalue`;
CREATE TABLE `evalvalue` (
`idevalvalue` int(11)   NULL  default '' comment '',
`idstockinfo` int(11)   NULL  default '' comment '',
`ownerearnings` float(10)   NULL  default '' comment '',
`discountrate` int(11)   NULL  default '' comment '',
`incomegrowth` int(11)   NULL  default '' comment 'year over year growth percentage',
`value` int(11)   NULL  default '' comment '',
`simple` tinyint(1)   NULL  default '' comment '',
`valueowners` tinyint(1)   NULL  default '' comment '',
`benefitreinvest` tinyint(1)   NULL  default '' comment '',
`expandbypurchase` tinyint(1)   NULL  default '' comment '',
`regulated` tinyint(1)   NULL  default '' comment '',
`neededproduct` tinyint(1)   NULL  default '' comment '',
`closesubstitute` tinyint(1)   NULL  default '' comment '',
`mimiccompetition` tinyint(1)   NULL  default '' comment '',
`hyperactivity` tinyint(1)   NULL  default '' comment '',
`kellyoptimization` float(10)   NULL  default '' comment '',
`riskprobability` float(10)   NULL  default '' comment '',
`cosnsistanthistory` tinyint(1)   NULL  default '' comment '',
`communicatemorethangaap` tinyint(1)   NULL  default '' comment '',
`publicconfession` tinyint(1)   NULL  default '' comment '',
`retainearningsmv` tinyint(1)   NULL  default '' comment '',
`debtratio` float(10)   NULL  default '' comment '',
`acceptabledebt` float(10)   NULL  default '' comment '',
`roe` tinyint(1)   NULL  default '' comment '',
`lowcost` tinyint(1)   NULL  default '' comment '',
`frfeqreorg` tinyint(1)   NULL  default '' comment '',
`netincome` float(10)   NULL  default '' comment '',
`depreciation` float(10)   NULL  default '' comment '',
`depletion` float(10)   NULL  default '' comment '',
`amortization` float(10)   NULL  default '' comment '',
`capitalexpenses` float(10)   NULL  default '' comment '',
`workingcapital` float(10)   NULL  default '' comment '',
`marketcap` float(10)   NULL  default '' comment '',
`marginsafety` float(10)   NULL  default '' comment '', PRIMARY KEY (`idevalvalue`)) ENGINE=InnoDB;

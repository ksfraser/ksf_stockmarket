-- MySQL dump 10.11
--
-- Host: localhost    Database: finance
-- ------------------------------------------------------
-- Server version	5.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `candlesticksoccured`
--

DROP TABLE IF EXISTS `candlesticksoccured`;
CREATE TABLE `candlesticksoccured` (
  `idcandlesticksoccured` int(11) NOT NULL auto_increment COMMENT 'Index',
  `createddate` datetime NOT NULL default '2009-01-01 00:00:00' COMMENT 'Record Created Date',
  `createduser` int(11) NOT NULL default '0' COMMENT 'Record Created by User',
  `updateddate` timestamp NOT NULL default CURRENT_TIMESTAMP COMMENT 'Record updated date',
  `updateduser` int(11) NOT NULL default '0' COMMENT 'Record Updated by user',
  `symbol` varchar(11) NOT NULL default '' COMMENT 'Stock Symbol',
  `date` date NOT NULL default '0000-00-00' COMMENT 'Date in stockprices',
  `candlestick` varchar(255) NOT NULL default '' COMMENT 'Candlestick Identified for this date',
  PRIMARY KEY  (`idcandlesticksoccured`),
  UNIQUE KEY `date_symbol` (`date`,`symbol`,`candlestick`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 ROW_FORMAT=DYNAMIC COMMENT='What candlesticks occurred for what stocks on what date';

--
-- Dumping data for table `candlesticksoccured`
--

LOCK TABLES `candlesticksoccured` WRITE;
/*!40000 ALTER TABLE `candlesticksoccured` DISABLE KEYS */;
/*!40000 ALTER TABLE `candlesticksoccured` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2010-08-22 18:39:49

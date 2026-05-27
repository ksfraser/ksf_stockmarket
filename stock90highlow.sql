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
-- Table structure for table `stock90highlow`
--

DROP TABLE IF EXISTS `stock90highlow`;
CREATE TABLE `stock90highlow` (
  `idstock90highlow` int(10) NOT NULL auto_increment COMMENT 'Index',
  `stocksymbol` int(10) unsigned NOT NULL default '62' COMMENT 'Stock Symbol',
  `high` float NOT NULL default '0',
  `low` float NOT NULL default '0',
  `currentprice` float NOT NULL default '0',
  `idstockinfo` int(10) unsigned NOT NULL,
  `createddate` timestamp NOT NULL default '0000-00-00 00:00:00',
  `createduser` varchar(45) NOT NULL default '',
  `reviseddate` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `reviseduser` varchar(45) NOT NULL default '',
  `active` int(1) NOT NULL default '1' COMMENT 'Is this symbol still active',
  `cik` varchar(11) NOT NULL COMMENT 'SECs CIK value for the company',
  PRIMARY KEY  (`idstock90highlow`),
  UNIQUE KEY `symbol` (`stocksymbol`),
  KEY `active_index` (`active`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 ROW_FORMAT=COMPACT;

--
-- Dumping data for table `stock90highlow`
--

LOCK TABLES `stock90highlow` WRITE;
/*!40000 ALTER TABLE `stock90highlow` DISABLE KEYS */;
/*!40000 ALTER TABLE `stock90highlow` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2013-11-16  5:48:18

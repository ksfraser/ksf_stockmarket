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
-- Table structure for table `dividendpayment`
--

DROP TABLE IF EXISTS `dividendpayment`;
CREATE TABLE `dividendpayment` (
  `iddividendpayment` int(10) unsigned NOT NULL auto_increment COMMENT 'Index',
  `stocksymbol` varchar(45) NOT NULL default '',
  `dividendpershare` float NOT NULL default '0' COMMENT 'Dividend Per Share',
  `lastupdate` timestamp NOT NULL default CURRENT_TIMESTAMP COMMENT 'Last Updated',
  `idstockexchange` int(11) NOT NULL COMMENT 'The Exchange the stock is on',
  `exdividenddate` date NOT NULL COMMENT 'The date the owner of record for the stock is used to pay the dividend',
  `idstockinfo` int(11) NOT NULL COMMENT 'The Stockinfo Index',
  PRIMARY KEY  (`iddividendpayment`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `dividendpayment`
--

LOCK TABLES `dividendpayment` WRITE;
/*!40000 ALTER TABLE `dividendpayment` DISABLE KEYS */;
/*!40000 ALTER TABLE `dividendpayment` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2014-02-15 21:42:08

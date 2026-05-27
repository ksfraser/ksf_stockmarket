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
-- Table structure for table `turtledata`
--

DROP TABLE IF EXISTS `turtledata`;
CREATE TABLE `turtledata` (
  `idturtledata` int(11) NOT NULL COMMENT 'Index of table',
  `symbol` varchar(6) NOT NULL COMMENT 'The stock symbol',
  `date` date NOT NULL COMMENT 'The date this data is for',
  `createddate` datetime NOT NULL COMMENT 'Date the record was created',
  `createduser` int(11) NOT NULL COMMENT 'Record created by user',
  `updateddate` timestamp NOT NULL default '0000-00-00 00:00:00' on update CURRENT_TIMESTAMP COMMENT 'date record was updated',
  `updateduser` int(11) NOT NULL COMMENT 'record updated by user',
  `volatility` float NOT NULL COMMENT 'The volatility (N) of the market',
  `unit` float NOT NULL COMMENT 'The unit size of the market',
  `breakouthigh20` float NOT NULL COMMENT 'The 20 day high breakout value',
  `breakoutlow20` float NOT NULL COMMENT 'The low 20 day breakout price',
  `breakouthigh55` float NOT NULL COMMENT 'The high 55 day breakout price',
  `breakoutlow55` float NOT NULL COMMENT 'The 55 day low breakout value',
  `low10` float NOT NULL COMMENT 'The 10 day low for selling longs',
  `high10` float NOT NULL COMMENT 'The 10 day high used for selling shorts',
  `low20` float NOT NULL COMMENT 'The 20 day low price',
  `high20` float NOT NULL COMMENT 'The 20 day high price',
  `truerange` float NOT NULL COMMENT 'True range - MAX( High0-Low0, High0-Close1, Close1 - Low0 )',
  `ignore20` int(1) NOT NULL COMMENT 'Was the 20 day signal ignored due to the winning trade rule',
  `positionadd` float NOT NULL COMMENT 'Once a breakout occurs, you can add to the position at 1/2N prices.  What is the next 1/2N price',
  `sellallprice` float NOT NULL COMMENT 'All units are sold if the breakout20 is reached before the 10 day exit price',
  `normalizedprice` float NOT NULL COMMENT 'Normalized price of the market - Current Price - 90day EMA divided by N',
  PRIMARY KEY  (`symbol`,`date`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 COMMENT='Data used for the Original Turtles trading method';

--
-- Dumping data for table `turtledata`
--

LOCK TABLES `turtledata` WRITE;
/*!40000 ALTER TABLE `turtledata` DISABLE KEYS */;
/*!40000 ALTER TABLE `turtledata` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2009-09-19 23:53:43

-- MySQL dump 10.10
--
-- Host: localhost    Database: stocks
-- ------------------------------------------------------
-- Server version	5.0.15-nt

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
-- Table structure for table `portfolio`
--

create database stocks;
grant ALL on stocks.* to investing@localhost identified by 'investing';
use stocks;

DROP TABLE IF EXISTS `portfolio`;
CREATE TABLE `portfolio` (
  `symbol` char(4) NOT NULL,
  `number` int(10) unsigned NOT NULL,
  `cost` int(10) unsigned NOT NULL,
  `user` varchar(45) NOT NULL,
  PRIMARY KEY  (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `portfolio`
--


/*!40000 ALTER TABLE `portfolio` DISABLE KEYS */;
LOCK TABLES `portfolio` WRITE;
UNLOCK TABLES;
/*!40000 ALTER TABLE `portfolio` ENABLE KEYS */;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
  `sequence` int(10) unsigned NOT NULL auto_increment,
  `roledesc` varchar(45) NOT NULL default 'SET ME',
  `rolenumber` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`sequence`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `roles`
--


/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
LOCK TABLES `roles` WRITE;
UNLOCK TABLES;
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;

--
-- Table structure for table `stockinfo`
--

DROP TABLE IF EXISTS `stockinfo`;
CREATE TABLE `stockinfo` (
  `stocksymbol` char(4) NOT NULL,
  `exchange` varchar(45) NOT NULL,
  `corporatename` varchar(255) NOT NULL,
  `52high` double NOT NULL,
  `52low` double NOT NULL,
  `high` double NOT NULL,
  `low` double NOT NULL,
  PRIMARY KEY  (`stocksymbol`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `stockinfo`
--


/*!40000 ALTER TABLE `stockinfo` DISABLE KEYS */;
LOCK TABLES `stockinfo` WRITE;
INSERT INTO `stockinfo` VALUES ('RNK','TSX','RainMaker Income Trust Fund',4,3,4.2,3);
UNLOCK TABLES;
/*!40000 ALTER TABLE `stockinfo` ENABLE KEYS */;

--
-- Table structure for table `tenets`
--

DROP TABLE IF EXISTS `tenets`;
CREATE TABLE `tenets` (
  `symbol` char(4) NOT NULL default 'ABCD',
  `simple` int(10) unsigned NOT NULL default '0',
  `consistent` int(10) unsigned NOT NULL default '0',
  `longterm` int(10) unsigned NOT NULL default '0',
  `rationalmanager` int(10) unsigned NOT NULL default '0',
  `candid` int(10) unsigned NOT NULL default '0',
  `resistinstitute` int(10) unsigned NOT NULL default '0',
  `focusroe` int(10) unsigned NOT NULL default '0',
  `ownerearnings` int(10) unsigned NOT NULL default '0',
  `highprofitmargin` int(10) unsigned NOT NULL default '0',
  `retainedtomarket` int(10) unsigned NOT NULL default '0',
  `valueofbusiness` int(10) unsigned NOT NULL default '0',
  `discounted` int(10) unsigned NOT NULL default '0',
  PRIMARY KEY  (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `tenets`
--


/*!40000 ALTER TABLE `tenets` DISABLE KEYS */;
LOCK TABLES `tenets` WRITE;
UNLOCK TABLES;
/*!40000 ALTER TABLE `tenets` ENABLE KEYS */;

--
-- Table structure for table `transaction`
--

DROP TABLE IF EXISTS `transaction`;
CREATE TABLE `transaction` (
  `sequence` int(11) NOT NULL auto_increment,
  `user` varchar(45) NOT NULL default ' ',
  `stocksymbol` char(4) NOT NULL default '',
  `number` int(11) NOT NULL,
  `transactiontype` varchar(45) NOT NULL,
  `dollar` float NOT NULL,
  PRIMARY KEY  (`sequence`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `transaction`
--


/*!40000 ALTER TABLE `transaction` DISABLE KEYS */;
LOCK TABLES `transaction` WRITE;
INSERT INTO `transaction` VALUES (1,'kevin','RNK',100,' BUY',300),(2,'kevin','RNK',100,' BUY',300),(3,'kevin','RNK',100,' BUY',300);
UNLOCK TABLES;
/*!40000 ALTER TABLE `transaction` ENABLE KEYS */;

--
-- Table structure for table `transactiontype`
--

DROP TABLE IF EXISTS `transactiontype`;
CREATE TABLE `transactiontype` (
  `transactiontype` varchar(45) NOT NULL,
  PRIMARY KEY  (`transactiontype`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `transactiontype`
--


/*!40000 ALTER TABLE `transactiontype` DISABLE KEYS */;
LOCK TABLES `transactiontype` WRITE;
INSERT INTO `transactiontype` VALUES (' BUY'),(' DIVIDEND'),(' EXCHANGE'),(' SELL'),(' SPLIT'),(' TAKEOVER'),(' TRANSFER');
UNLOCK TABLES;
/*!40000 ALTER TABLE `transactiontype` ENABLE KEYS */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `username` varchar(255) NOT NULL,
  `surname` varchar(45) NOT NULL,
  `firstname` varchar(45) NOT NULL,
  `emailaddress` varchar(255) NOT NULL,
  `password` varchar(45) NOT NULL,
  `role` int(10) unsigned zerofill NOT NULL default '0000000000' COMMENT 'Binary Bit representation of access',
  PRIMARY KEY  (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `users`
--


/*!40000 ALTER TABLE `users` DISABLE KEYS */;
LOCK TABLES `users` WRITE;
INSERT INTO `users` VALUES ('kevin','Fraser','Kevin',' kevin@defiant.airdrie.fraser','letmein',0000000000),('test','test','test','test@test.com','test',0000000000),('tester','tester','tester','tester@terster.com','tester',0000000000);
UNLOCK TABLES;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;


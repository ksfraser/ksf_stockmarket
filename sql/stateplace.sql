DROP TABLE IF EXISTS `stateplace`;
CREATE TABLE `stateplace` (
`workflow_id` smallint(5) unsigned  NULL  default '' comment 'Workflow Process',
`place_id` smallint(5) unsigned  NULL  default '' comment 'Index',
`place_type` char(1)   NULL  default '' comment 'Type',
`place_name` varchar(80)   NULL  default '' comment 'Name',
`place_desc` text(255)   NOT NULL  default '' comment 'Description',
`created_date` datetime(17)   NULL  default '' comment 'Created Date',
`created_user` varchar(16)   NOT NULL  default '' comment 'Created By User',
`revised_date` datetime(17)   NOT NULL  default '' comment 'Revision Date',
`revised_user` varchar(16)   NOT NULL  default '' comment 'Revised by User', PRIMARY KEY (`place_id`)) ENGINE=InnoDB;

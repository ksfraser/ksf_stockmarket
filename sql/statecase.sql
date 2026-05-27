DROP TABLE IF EXISTS `statecase`;
CREATE TABLE `statecase` (
`case_id` int(10) unsigned  NULL  default '' comment 'Index',
`workflow_id` smallint(5) unsigned  NULL  default '' comment 'Workflow Process',
`context` varchar(255)   NULL  default '' comment 'Context',
`case_status` char(2)   NULL  default '' comment 'Status',
`start_date` datetime()   NULL  default '' comment 'Start Date',
`end_date` datetime()   NOT NULL  default '' comment 'End Date',
`created_date` datetime()   NULL  default '' comment 'Created Date',
`created_user` varchar(16)   NOT NULL  default '' comment 'Created By User',
`revised_date` datetime()   NOT NULL  default '' comment 'Revision Date',
`revised_user` varchar(16)   NOT NULL  default '' comment 'Revised by User', PRIMARY KEY (`case_id`)) ENGINE=InnoDB;

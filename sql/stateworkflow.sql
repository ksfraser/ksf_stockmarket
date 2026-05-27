DROP TABLE IF EXISTS `stateworkflow`;
CREATE TABLE `stateworkflow` (
`workflow_id` smallint(5) unsigned  NULL  default '' comment 'Workflow Process',
`workflow_name` varchar(80)   NULL  default '' comment 'Workflow Name',
`workflow_desc` text(255)   NOT NULL  default '' comment 'Workflow Description',
`idtasks` varchar(40)   NULL  default '' comment 'Start Task',
`is_valid` char(1)   NULL  default '' comment 'Valid Flag',
`workflow_errors` text(17)   NOT NULL  default '' comment 'Errors',
`start_date` date(17)   NOT NULL  default '2007-01-01' comment 'Start Date',
`end_date` date(17)   NOT NULL  default '2007-01-01' comment 'End Date',
`created_date` datetime(17)   NULL  default '' comment 'Created Date',
`created_user` varchar(16)   NOT NULL  default '' comment 'Created By User',
`revised_date` datetime(17)   NOT NULL  default '' comment 'Last Revised Date',
`revised_user` varchar(16)   NOT NULL  default '' comment 'Last Revised by User', PRIMARY KEY (`workflow_id`)) ENGINE=InnoDB;

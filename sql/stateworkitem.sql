DROP TABLE IF EXISTS `stateworkitem`;
CREATE TABLE `stateworkitem` (
`case_id` int(10) unsigned  NULL  default '' comment 'Case',
`workitem_id` smallint(5) unsigned  NULL  default '' comment 'Index',
`workflow_id` smallint(6) unsigned  NULL  default '' comment 'Workflow Process',
`transition_id` smallint(5) unsigned  NULL  default '' comment 'Transition',
`transition_trigger` varchar(4)   NULL  default '' comment 'Trigger',
`task_id` varchar(40)   NULL  default '' comment 'Task',
`context` varchar(255)   NULL  default '' comment 'Context',
`workitem_status` char(2)   NULL  default '' comment 'Status',
`enabled_date` datetime()   NOT NULL  default '' comment 'Enabled Date',
`cancelled_date` datetime()   NOT NULL  default '' comment 'Cancelled Date',
`finished_date` datetime()   NOT NULL  default '' comment 'Finished Date',
`deadline` datetime()   NOT NULL  default '' comment 'Deadline',
`role_id` varchar(16)   NOT NULL  default '' comment 'Role',
`user_id` varchar(16)   NOT NULL  default '' comment 'User', PRIMARY KEY (`case_id`, 'case_id', 'workitem_id')) ENGINE=InnoDB;

DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
`h_role_access` int(8)   NOT NULL  default '' comment 'Role Access Number - 2 ^ (id - 1)',
`h_compesate_access` double(16)   NOT NULL  default '0' comment 'A composate Role Access Number',
`roledescription` varchar(45)   NOT NULL  default '' comment 'Role Description',
`roles_id` integer(8)   NOT NULL  default '0' comment 'Role Index', PRIMARY KEY (`roles_id`)) ENGINE=InnoDB;

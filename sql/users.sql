DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
`username` varchar(255)   NOT NULL  default '' comment 'UserName',
`surname` varchar(45)   NOT NULL  default '' comment 'Surname',
`firstname` varchar(45)   NOT NULL  default '' comment 'Firstname',
`emailaddress` varchar(255)   NOT NULL  default '' comment 'Email Address',
`password` varchar(45)   NOT NULL  default '' comment 'Password',
`roles_id` integer(8)   NOT NULL  default '' comment 'Role Access Control', PRIMARY KEY (``)) ENGINE=InnoDB;

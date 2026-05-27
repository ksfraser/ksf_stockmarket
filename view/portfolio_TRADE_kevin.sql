create view portfolio_TRADE_kevin as select * from portfolio where username='kevin' and numbershares <>0 and account='TRADE';
create view portfolio_RRSP_kevin as select * from portfolio where username='kevin' and numbershares <>0 and account='RRSP';
create view portfolio_TFSA_kevin as select * from portfolio where username='kevin' and numbershares <>0 and account='TFSA';
create view portfolio_ALL_kevin as select * from portfolio where username='kevin' and numbershares <>0 and account='ALL';



delimiter |
use finance|

CREATE TRIGGER users_portfolioTypes_AI AFTER INSERT ON users
  FOR EACH ROW BEGIN
	declare username varchar(32);
	declare accounttypes varchar(32);
	if new.username is not null then
		set username = new.username;
		accounttypes = select accounttype from accounttype;
	end if;
  END;
|

delimiter ;


drop trigger emps.bi_emps_fer
//

create trigger bi_emps_fer before insert on emps for each row
begin
    declare newsal numeric default 0;
    declare namelength, l_loop int default 0;
if new.emp_name is not null then
    set namelength = length(new.emp_name);
    while l_loop < namelength do
       set newsal := newsal   new.salary;
       set l_loop := l_loop   1;
    end while;
    set new.salary = newsal;
end if;
end


CREATE PROCEDURE adjust_emp_salary () 
BEGIN 
  DECLARE job_id INT;
  DECLARE employee_id INT DEFAULT 115;
  DECLARE sal_raise DECIMAL(3,2);
  DECLARE EXIT HANDLER FOR 1339; 
 
  SELECT job_id INTO jobid FROM employees WHERE employee_id = empid;
  CASE
    WHEN jobid = 'PU_CLERK' THEN 
      SET sal_raise := .09;
    WHEN jobid = 'SH_CLERK' THEN 
      SET sal_raise := .08;
    WHEN jobid = 'ST_CLERK' THEN 
      SET sal_raise := .07;
  END CASE;
END;


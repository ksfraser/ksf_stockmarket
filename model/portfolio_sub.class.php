<?php

require_once( 'portfolio.class.php' );

class portfolio_sub extends portfolio
{
	function __construct()
	{
		parent::__construct();
		$substitute = "portfolio_" . $_SESSION['accounttype'] . "_" . $_SESSION['username'];
		$this->querytablename = $substitute;
		$this->classname = $substitute;

		$this->fieldspec['username']['table_name'] = $substitute;
                $this->fieldspec['username']['extra_sql'] = '<sql><select><where><v1>_' . $substitute . '.username</v1><op>=</op><v2>currentuser</v2></where><orderby>' . $substitute . '.stocksymbol</orderby></select></sql>';
                $this->fieldspec['account']['table_name'] = $substitute;
                $this->fieldspec['stocksymbol']['table_name'] = $substitute;
                $this->fieldspec['numbershares']['table_name'] = $substitute;
                $this->fieldspec['bookvalue']['table_name'] = $substitute;
                $this->fieldspec['dividendbookvalue']['table_name'] = $substitute;
                $this->fieldspec['marketvalue']['table_name'] = $substitute;
                $this->fieldspec['profitloss']['table_name'] = $substitute;
                $this->fieldspec['marketbook']['table_name'] = $substitute;
                $this->fieldspec['yield']['table_name'] = $substitute;
                $this->fieldspec['currentprice']['table_name'] = $substitute;
                $this->fieldspec['annualdividendpershare']['table_name'] = $substitute;
                $this->fieldspec['annualdividend']['table_name'] = $substitute;
                $this->fieldspec['dividendpercentbookvalue']['table_name'] = $substitute;
                $this->fieldspec['dividendpercentmarketvalue']['table_name'] = $substitute;
                $this->fieldspec['dividendyield']['table_name'] = $substitute;
                $this->fieldspec['percenttotalmarketvalue']['table_name'] = $substitute;
                $this->fieldspec['percenttotalbookvalue']['table_name'] = $substitute;
                $this->fieldspec['percenttotaldividend']['table_name'] = $substitute;
                $this->fieldspec['lastupdate']['table_name'] = $substitute;

	}

}
?>

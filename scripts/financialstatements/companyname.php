<?php

//Get the company name from a google financial report
//Google uses a common format for the header of the page - 
//  <title>Financial Statements for iShares CDN S&P/TSX 60 Index Fund - Google Finance</title>


function getCompanyName( $page )
{
	preg_match("/(?P<title><title>Financial Statements for )(?P<companyname>.*)(?P<etitle> - Google )/",
		$page,
                $matches);
	echo "<br />companyname::getCompanyName <br />\n";
//	var_dump( $matches );
	return $matches['companyname'];
}


//TEST
//	$name = getCompanyName( "<body><title>Financial Statements for iShares CDN S&P/TSX 60 Index Fund - Google Finance</title> </body>" );
//	echo "\nCompany Name is $name\n";

?>

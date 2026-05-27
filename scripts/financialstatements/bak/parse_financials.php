<?php

	//Take a web page of financials from GOOGLE
	//and parse it to send the values to the
	//tenets tables

//20090606 KF Eventum 152
//	Add a ratios table
//20090606 KF Eventum 153
//	Correct calculation of Capital Expense, Net Income Growth, Revenu Growth 1,2 3
//20090824 KF Eventum 166
//	Google changed their URL
//	Refactor

require_once( 'companyname.php' ); //strip the company name out of the <title> tag
require_once( 'googledownloadstatement.php' ); 
require_once( '../fundamentalanalysis/earningsaccel.php' );
require_once( '../fundamentalanalysis/earningsgrowth.php' );
require_once( '../fundamentalanalysis/dividendincreases.php' );
require_once( '../fundamentalanalysis/shareholderprofitgoal.php' );


function parse_data( $data )
{
	list( $a1, $a2, $a3, $a4, $a5, $a6, $a7, $a8, $a9 ) = explode( "<table", $data );
//var_dump( $a8 );
//list( $a1r1, $a1r2, $a1r3, $a1r4, $a1r5, $a1r6, $a1r7, $a1r8 ) = explode( "<tr", $a1 );
//list( $a2r1, $a2r2, $a2r3, $a2r4, $a2r5, $a2r6, $a2r7, $a2r8 ) = explode( "<tr", $a2 );
	list( $a3r1, $a3r2, $a3r3 ) = explode( "<tr", $a3 );
	//Monthly income
	list( $a4r1, $a4r2, $a4r3, $a4r4, $a4r5, $a4r6, $a4r7, $a4r8, $a4r9,
		$a4r10, $a4r11, $a4r12, $a4r13, $a4r14, $a4r15, $a4r16, $a4r17, $a4r18, $a4r19,
		$a4r20, $a4r21, $a4r22, $a4r23, $a4r24, $a4r25, $a4r26, $a4r27, $a4r28, $a4r29,
		$a4r30, $a4r31, $a4r32, $a4r33, $a4r34, $a4r35, $a4r36, $a4r37, $a4r38, $a4r39,
		$a4r40, $a4r41, $a4r42, $a4r43, $a4r44, $a4r45, $a4r46, $a4r47, $a4r48, $a4r49,
		$a4r50, $a4r51, $a4r52, $a4r53, $a4r54, $a4r55, $a4r56, $a4r57, $a4r58, $a4r59
	) = explode( "<tr", $a4 );
	//Annual Income
	list( $a5r1, $a5r2, $a5r3, $a5r4, $a5r5, $a5r6, $a5r7, $a5r8, $a5r9,
		$a5r10, $a5r11, $a5r12, $a5r13, $a5r14, $a5r15, $a5r16, $a5r17, $a5r18, $a5r19,
		$a5r20, $a5r21, $a5r22, $a5r23, $a5r24, $a5r25, $a5r26, $a5r27, $a5r28, $a5r29,
		$a5r30, $a5r31, $a5r32, $a5r33, $a5r34, $a5r35, $a5r36, $a5r37, $a5r38, $a5r39,
		$a5r40, $a5r41, $a5r42, $a5r43, $a5r44, $a5r45, $a5r46, $a5r47, $a5r48, $a5r49,
		$a5r50, $a5r51, $a5r52, $a5r53, $a5r54, $a5r55, $a5r56, $a5r57, $a5r58, $a5r59
	) = explode( "<tr", $a5 );
	//Intermediate balance
	list( 	$a6r1, $a6r2, $a6r3, $a6r4, $a6r5, $a6r6, $a6r6, $a6r8, $a6r9, 
		$a6r10, $a6r11, $a6r12, $a6r13, $a6r14, $a6r15, $a6r16, $a6r17, $a6r18, $a6r19,
		$a6r20, $a6r21, $a6r22, $a6r23, $a6r24, $a6r25, $a6r26, $a6r27, $a6r28, $a6r29,
		$a6r30, $a6r31, $a6r32, $a6r33, $a6r34, $a6r35, $a6r36, $a6r37, $a6r38, $a6r39,
		$a6r40, $a6r41, $a6r42, $a6r43, $a6r44, $a6r45, $a6r46, $a6r47, $a6r48, $a6r49,
		$a6r50, $a6r51, $a6r52
    	) = explode( "<tr", $a6 );
	//Annual Balance sheet
	list( 	$a7r1, $a7r2, $a7r3, $a7r4, $a7r5, $a7r6, $a7r7, $a7r8, $a7r9, 
		$a7r10, $a7r11, $a7r12, $a7r13, $a7r14, $a7r15, $a7r16, $a7r17, $a7r18, $a7r19,
		$a7r20, $a7r21, $a7r22, $a7r23, $a7r24, $a7r25, $a7r26, $a7r27, $a7r28, $a7r29,
		$a7r30, $a7r31, $a7r32, $a7r33, $a7r34, $a7r35, $a7r36, $a7r37, $a7r38, $a7r39,
		$a7r40, $a7r41, $a7r42, $a7r43, $a7r44, $a7r45, $a7r46, $a7r47, $a7r48, $a7r49,
		$a7r50, $a7r51, $a7r52
    	) = explode( "<tr", $a7 );
	//Intermediate cash flow
	list( $a8r1, $a8r2, $a8r3, $a8r4, $a8r5, $a8r6, $a8r7, $a8r8, $a8r9, 
		$a8r10, $a8r11, $a8r12 ) = explode( "<tr", $a8 );
	//Annual cash flow
	list( $a9r1, $a9r2, $a9r3, $a9r4, $a9r5, $a9r6, $a9r7, $a9r8, $a9r9, 
		$a9r10, $a9r11, $a9r12 ) = explode( "<tr", $a9 );
//var_dump( $a3r2 );  //Page table
//var_dump( $a4r2 );  //Monthly Income
//var_dump( $a5r3 );  //Annual Income
//var_dump( $a6r3 );  //Intermediate Balance
//var_dump( $a7r3 );  //Annual Balance
//var_dump( $a7r50 );  //Outstanding Shares
//var_dump( $a8r3 );  //Intermediate Cash Flow
//var_dump( $a9r3 );  //Annual Cash Flow
	//Quarterly Income
	list( $a4r3t1, $a4r3t2, $a4r3t3, $a4r3t4, $a4r3t5, $a4r3t6 ) = explode( "<td", $a4r3 );
	//Quarterly Cash Flow
	list( $a8r2t1, $a8r2t2, $a8r2t3, $a8r2t4, $a8r2t5, $a8r2t6 ) = explode( "<td", $a8r2 );
	list( $a8r3t1, $a8r3t2, $a8r3t3, $a8r3t4, $a8r3t5, $a8r3t6, $a8r3t7 ) = explode( "<td", $a8r3 );
	list( $a8r4t1, $a8r4t2, $a8r4t3, $a8r4t4, $a8r4t5, $a8r4t6 ) = explode( "<td", $a8r4 );
	list( $a8r5t1, $a8r5t2, $a8r5t3, $a8r5t4, $a8r5t5, $a8r5t6 ) = explode( "<td", $a8r5 );
	list( $a8r6t1, $a8r6t2, $a8r6t3, $a8r6t4, $a8r6t5, $a8r6t6 ) = explode( "<td", $a8r6 );
	list( $a8r7t1, $a8r7t2, $a8r7t3, $a8r7t4, $a8r7t5, $a8r7t6 ) = explode( "<td", $a8r7 );
	list( $a8r8t1, $a8r8t2, $a8r8t3, $a8r8t4, $a8r8t5, $a8r8t6 ) = explode( "<td", $a8r8 );
	list( $a8r11t1, $a8r11t2, $a8r11t3, $a8r11t4, $a8r11t5, $a8r11t6 ) = explode( "<td", $a8r11 );
	list( $a8r12t1, $a8r12t2, $a8r12t3, $a8r12t4, $a8r12t5, $a8r12t6 ) = explode( "<td", $a8r12 );
	list( $a7r51t1, $a7r51t2, $a7r51t3, $a7r51t4, $a7r51t5, $a7r51t6 ) = explode( "<td", $a7r51 );
	//list( $a7r49t1, $a7r49t2, $a7r49t3, $a7r49t4, $a7r49t5, $a7r49t6 ) = explode( "<td", $a7r49 );
	list( $a7r49t1, $a7r49t2 ) = explode( "<td", $a7r49 );
	list( $a7r48t1, $a7r48t2, $a7r48t3, $a7r48t4, $a7r48t5, $a7r48t6 ) = explode( "<td", $a7r48 );
	//Annual Income
	list( $a5r3t1, $a5r3t2, $a5r3t3, $a5r3t4, $a5r3t5, $a5r3t6 ) = explode( "<td", $a5r3 );
	//Annual Cash Flow
	list( $a9r2t1, $a9r2t2, $a9r2t3, $a9r2t4, $a9r2t5, $a9r2t6 ) = explode( "<td", $a9r2 );
	list( $a9r3t1, $a9r3t2, $a9r3t3, $a9r3t4, $a9r3t5, $a9r3t6, $a9r3t7 ) = explode( "<td", $a9r3 );
	list( $a9r4t1, $a9r4t2, $a9r4t3, $a9r4t4, $a9r4t5, $a9r4t6 ) = explode( "<td", $a9r4 );
	list( $a9r5t1, $a9r5t2, $a9r5t3, $a9r5t4, $a9r5t5, $a9r5t6 ) = explode( "<td", $a9r5 );
	list( $a9r6t1, $a9r6t2, $a9r6t3, $a9r6t4, $a9r6t5, $a9r6t6 ) = explode( "<td", $a9r6 );
	list( $a9r7t1, $a9r7t2, $a9r7t3, $a9r7t4, $a9r7t5, $a9r7t6 ) = explode( "<td", $a9r7 );
	list( $a9r8t1, $a9r8t2, $a9r8t3, $a9r8t4, $a9r8t5, $a9r8t6 ) = explode( "<td", $a9r8 );
	list( $a9r11t1, $a9r11t2, $a9r11t3, $a9r11t4, $a9r11t5, $a9r11t6 ) = explode( "<td", $a9r11 );
	list( $a9r12t1, $a9r12t2, $a9r12t3, $a9r12t4, $a9r12t5, $a9r12t6 ) = explode( "<td", $a9r12 );
	list( $a7r51t1, $a7r51t2, $a7r51t3, $a7r51t4, $a7r51t5, $a7r51t6 ) = explode( "<td", $a7r51 );
	//list( $a7r49t1, $a7r49t2, $a7r49t3, $a7r49t4, $a7r49t5, $a7r49t6 ) = explode( "<td", $a7r49 );
	list( $a7r49t1, $a7r49t2 ) = explode( "<td", $a7r49 );
	list( $a7r48t1, $a7r48t2, $a7r48t3, $a7r48t4, $a7r48t5, $a7r48t6 ) = explode( "<td", $a7r48 );
	//var_dump( $a9r3t2 );  //Net Income
	$tok = strtok( $a8r3t3, ";" );
	$qnetincome = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a9r3t3, ";" );
	$netincome = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a9r3t4, ";" );
	$netincome1 = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a9r3t5, ";" );
	$netincome2 = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a9r3t6, ";" );
	$netincome3 = str_replace( $bad, $good, strtok( "&" ));
	//$tok = strtok( $a9r3t7, ";" );
	//$netincome4 = str_replace( $bad, $good, strtok( "&" ));
	//var_dump( $a9r4t2 );  //Depreciation
	$tok = strtok( $a8r4t3, ";" );
	$qdepreciation = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a9r4t3, ";" );
	$depreciation = str_replace( $bad, $good, strtok( "&" ));
	//var_dump( $a9r5t2 );  //Amortization
	//$tok = strtok( $a9r5t3, ">" );
	list( $a, $b ) = explode( "chr>", $a9r4t3 );
	$qamortization = str_replace( $bad, $good, strtok( $b, "&" ));
	list( $a, $b ) = explode( "chr>", $a9r5t3 );
	$amortization = str_replace( $bad, $good, strtok( $b, "&" ));
	//$amortization = split( "chr>" );
	//var_dump( $a9r6t2 );  //Defered Taxes
	//$tok = strtok( $a9r6t3, ";" );
	//$deferredtaxes = strtok( "&" );
	//var_dump( $a9r7t2 );  //Non Cash
	//$tok = strtok( $a9r7t3, ";" );
	//$totalassets = strtok( "&" );
	////echo "Working Capital raw\n";
	//var_dump( $a9r8t2 );  //Working Capital
	//var_dump( $a9r8t3 );  //Working Capital
	//list( $a, $b ) = explode( "chr>", $a9r8t3 );
	//var_dump( $b );
	$tok = strtok( $a8r8t3, ";" );
	$qworkingcapital = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a9r8t3, ";" );
	$workingcapital = str_replace( $bad, $good, strtok( "&" ));
	//$workingcapital = strtok( $b, "&" );
	//r9 = Cash from operating activities
	//r10 is a line divider
	//var_dump( $a9r11t2 );  //Capital Expenditure
	list( $a, $b ) = explode( "chr>", $a8r11t3 );
	$qcapitalexpense = str_replace( $bad, $good, strtok( $b, "&" ));
	list( $a, $b ) = explode( "chr>", $a9r11t3 );
	//$tok = strtok( $a9r11t3, ";" );
	$capitalexpense = str_replace( $bad, $good, strtok( $b, "&" ));
	//$tok = strtok( $a7r51t3, ";" );

//OUTSTANDING SHARES
	////echo "Outstanding Shares raw\n";
	//var_dump( $a7r51t3 );
	list( $a, $b ) = explode( "b>", $a6r51t3 );
	$qshares = str_replace( $bad, $good, strtok( $b, "&" ));
	list( $a, $b ) = explode( "b>", $a7r51t3 );
	$shares = str_replace( $bad, $good, strtok( $b, "&" ));

	////echo "Company: $stocksymbol\n";
	//Growth
	if( $netincome1 <> 0 )
		$growth1 = ($netincome - $netincome1)  / $netincome1;
	if( $netincome2 <> 0 )
		$growth2 = ($netincome1 - $netincome2) / $netincome2;
/*
	if( $growth1 <= 1 )
		$growth1 = 0;
	if( $growth2 <= 1 )
		$growth2 = 0;
*/
	$growth = 100 * ( $growth1 + $growth2 ) / 2 - 100;
	////echo "Annual Growth: $growth\n";
//	////echo "Net Income : $netincome\n";
	if( $netincome == "-" )
		$netincome = 0;
	////echo "Net Income : $netincome\n";
//	//echo "Net Income1: $netincome1\n";
	if( $netincome1 == "-" )
		$netincome1 = 0;
	////echo "Net Income1: $netincome1\n";
//	//echo "Net Income2: $netincome2\n";
	if( $netincome2 == "-" )
		$netincome2 = 0;
	//echo "Net Income2: $netincome2\n";
	if( $netincome3 == "-" )
		$netincome3 = 0;
	//if( $netincome4 == "-" )
	//	$netincome4 = 0;
//	//echo "Depreciation: $depreciation\n";
	if( $depreciation == "-" )
		$depreciation = 0;
	//echo "Depreciation: $depreciation\n";
	$depletion = 0;
	//echo "Depletion: $depletion\n";
//	//echo "Amortization: $amortization\n";
	if( $amortization == "-" )
		$amortization = 0;
	//echo "Amortization: $amortization\n";
//	//echo "Working Capital: $workingcapital\n";
	if( $workingcapital == "-" )
		$workingcapital = 0;
	//echo "Working Capital: $workingcapital\n";
//	//echo "Capital Expenditures: $capitalexpense\n";
	if( $capitalexpense === "-" )
		$capitalexpense = 0;
	//echo "Capital Expenditures: $capitalexpense\n";
//	//echo "Outstanding Shares: $shares\n";
	if( $shares == "-" )
		$shares = 0;
	//echo "Outstanding Shares: $shares\n";

//match, repace, string

//Owner Earnings = Net Income + amortization + depreciation - Capital Expenses - Working Expenses + depletion
	$update['ownerearnings'] = (float)$netincome + (float)$amortization + (float)$depreciation - (float)$capitalexpense - (float)$workingcapital + $depletion;
	$update['incomegrowth'] = (float)$growth;
	$update['netincome'] = (float)$netincome;
	$update['revenuegrowth2'] = (float)$netincome - (float)$netincome2;
	$update['revenuegrowth3'] = (float)$netincome - (float)$netincome3;
	$update['revenuegrowth'] = (float)$netincome - (float)$netincome1;
	$update['earningsaccel'] = getEarningsAccel( $update );
	$update['earningsgrowth'] = getEarningsGrowth( $update );
	$update['depreciation'] = (float)$depreciation;
	$update['depletion'] = (float)$depletion;
	$update['amortization'] = (float)$amortization;
	$update['workingcapital'] = $workingcapital;
	$update['capitalexpenses'] = (float)$capitalexpense;
	$update['outstandingshares'] = (float)$shares * 1000000;

//Annual Balance Sheet - Assets and Liabilities
	$update['quarter']['idstockinfo'] = $idstockinfo;
	$update['quarter']['incomegrowth'] = (float)$qgrowth;
	$update['quarter']['netincome'] = (float)$qnetincome;
	$update['quarter']['revenuegrowth2'] = (float)$qnetincome - (float)$qnetincome2;
	$update['quarter']['revenuegrowth3'] = (float)$qnetincome - (float)$qnetincome3;
	$update['quarter']['revenuegrowth'] = (float)$qnetincome - (float)$qnetincome1;
	$update['quarter']['depreciation'] = (float)$qdepreciation;
	$update['quarter']['depletion'] = (float)$qdepletion;
	$update['quarter']['amortization'] = (float)$qamortization;
	$update['quarter']['workingcapital'] = $qworkingcapital;
	$update['quarter']['capitalexpenses'] = (float)$qcapitalexpense;
	$update['quarter']['outstandingshares'] = (float)$shares * 1000000;
	//var_dump( $a7 );
	//var_dump( $a7r19 );  //total liabilities
	//var_dump( $a7r37 );  //total assets
	list( $a6r19t1, $a6r19t2, $a6r19t3, $a6r19t4, $a6r19t5, $a6r19t6 ) = explode( "<td", $a6r19 );
	list( $a6r37t1, $a6r37t2, $a6r37t3, $a6r37t4, $a6r37t5, $a6r37t6 ) = explode( "<td", $a6r37 );
	list( $a6r32t1, $a6r32t2, $a6r32t3, $a6r32t4, $a6r32t5, $a6r32t6 ) = explode( "<td", $a6r32 );
	list( $a6r43t1, $a6r43t2, $a6r43t3, $a6r43t4, $a6r43t5, $a6r43t6 ) = explode( "<td", $a6r43 );
	list( $a6r46t1, $a6r46t2, $a6r46t3, $a6r46t4, $a6r46t5, $a6r46t6 ) = explode( "<td", $a6r46 );
	$tok = strtok( $a6r19t3, ";" );
	$update['quarter']['totalasset'] = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a6r37t3, ";" );
	$update['quarter']['totalliability'] =  str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a6r32t3, ";" );
	$update['quarter']['totaldebt'] = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a6r43t3, ";" );
	$update['quarter']['retainedearnings'] = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a6r46t3, ";" );
	$update['quarter']['totalequity'] = str_replace( $bad, $good, strtok( "&" ));
	list( $a4r3t1, $a4r3t2, $a4r3t3, $a4r3t4, $a4r3t5, $a4r3t6
		) = explode( "<td", $a4r3 );
	$tok = strtok( $a4r3t3, ";" );
	$update['quarter']['revenue'] = str_replace( $bad, $good, strtok( "&" ));
	//	var_dump( $a4r51 );
	list( $a4r47t1, $a4r47t2, $a4r47t3, $a4r47t4, $a4r47t5, $a4r47t6
		) = explode( "<td", $a4r47 );
	$tok = strtok( $a4r47t3, ";" );
	$update['quarter']['earningpershare'] = str_replace( $bad, $good, strtok( "&" ));
	if(  $update['quarter']['earningpershare'] == "-" )
		 $update['quarter']['earningpershare'] = "0.00";
	list( $a4r51t1, $a4r51t2, $a4r51t3, $a4r51t4, $a4r51t5, $a4r51t6
		) = explode( "<td", $a4r51 );
	$tok = strtok( $a4r51t3, ";" );
	$update['quarter']['dividendpershare'] = str_replace( $bad, $good, strtok( "&" ));
	if(  $update['quarter']['dividendpershare'] == "-" )
		 $update['quarter']['dividendpershare'] = "0.00";

	list( $a7r19t1, $a7r19t2, $a7r19t3, $a7r19t4, $a7r19t5, $a7r19t6 ) = explode( "<td", $a7r19 );
	list( $a7r37t1, $a7r37t2, $a7r37t3, $a7r37t4, $a7r37t5, $a7r37t6 ) = explode( "<td", $a7r37 );
	list( $a7r32t1, $a7r32t2, $a7r32t3, $a7r32t4, $a7r32t5, $a7r32t6 ) = explode( "<td", $a7r32 );
	list( $a7r43t1, $a7r43t2, $a7r43t3, $a7r43t4, $a7r43t5, $a7r43t6 ) = explode( "<td", $a7r43 );
	list( $a7r46t1, $a7r46t2, $a7r46t3, $a7r46t4, $a7r46t5, $a7r46t6 ) = explode( "<td", $a7r46 );
	$tok = strtok( $a7r19t3, ";" );
	$update['totalasset'] = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a7r37t3, ";" );
	$update['totalliability'] =  str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a7r32t3, ";" );
	$update['netvalue'] = $update['totalasset'] - $update['totalliability'];
	$update['totaldebt'] = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a7r43t3, ";" );
	$update['retainedearnings'] = str_replace( $bad, $good, strtok( "&" ));
	$tok = strtok( $a7r46t3, ";" );
	$update['totalequity'] = str_replace( $bad, $good, strtok( "&" ));
	list( $a5r3t1, $a5r3t2, $a5r3t3, $a5r3t4, $a5r3t5, $a5r3t6
		) = explode( "<td", $a5r3 );
	$tok = strtok( $a5r3t3, ";" );
	$update['revenue'] = str_replace( $bad, $good, strtok( "&" ));

	//var_dump( $a5r18 );
	list( $a5r18t1, $a5r18t2, $a5r18t3, $a5r18t4, $a5r18t5, $a5r18t6
		) = explode( "<td", $a5r18 );
	//var_dump( $a5r18t3 );
	$tok = strtok( $a5r18t3, ";" );
	$update['operatingincome'] = str_replace( $bad, $good, strtok( "&" ));
	list( $a5r8t1, $a5r8t2, $a5r8t3, $a5r8t4, $a5r8t5, $a5r8t6
		) = explode( "<td", $a5r8 );
	$tok = strtok( $a5r8t3, ";" );
	$update['grossprofit'] = str_replace( $bad, $good, strtok( "&" ));
	list( $a5r23t1, $a5r23t2, $a5r23t3, $a5r23t4, $a5r23t5, $a5r23t6
		) = explode( "<td", $a5r23 );
	$tok = strtok( $a5r23t3, ";" );
	$update['pretaxincome'] = str_replace( $bad, $good, strtok( "&" ));
	
	
	//	var_dump( $a5r51 );
		list( $a5r47t1, $a5r47t2, $a5r47t3, $a5r47t4, $a5r47t5, $a5r47t6
		) = explode( "<td", $a5r47 );
	$tok = strtok( $a5r47t3, ";" );
	$update['earningpershare'] = str_replace( $bad, $good, strtok( "&" ));
	if(  $update['earningpershare'] == "-" )
		 $update['earningpershare'] = "0.00";
	list( $a5r51t1, $a5r51t2, $a5r51t3, $a5r51t4, $a5r51t5, $a5r51t6
		) = explode( "<td", $a5r51 );
	$tok = strtok( $a5r51t3, ";" );
	$update['dividendpershare'] = str_replace( $bad, $good, strtok( "&" ));
	if(  $update['dividendpershare'] == "-" )
		 $update['dividendpershare'] = "0.00";
	$tok = strtok( $a5r51t4, ";" );
	$update['dividendpershare1'] = str_replace( $bad, $good, strtok( "&" ));
	if(  $update['dividendpershare1'] == "-" )
		 $update['dividendpershare1'] = "0.00";
	$tok = strtok( $a5r51t5, ";" );
	$update['dividendpershare2'] = str_replace( $bad, $good, strtok( "&" ));
	if(  $update['dividendpershare2'] == "-" )
		 $update['dividendpershare2'] = "0.00";
	$update['dividendincreases'] = getDividendIncreases( $update );
	$update['shareholderprofitgoal'] = getShareholderProfitGoal( $update );

//20090606 KF
//Eventum issue #152
//RATIOS

		//debtratio     totaldebt/totalassets
	$update['debtratio'] = $update['totaldebt'] / $update['totalasset'];
                //acceptabledebt netincome/revenue
	$update['acceptabledebtratio'] = $update['netincome'] / $update['revenue'];
                //roe  net_income/shareholder_equity - 15-20% is attractive investment
	if( $update['acceptabledebtratio'] > $update['debtratio'] )
	{
		$update['sustaindebtratio'] = 1;
	}
	else
	{
		$update['sustaindebtratio'] = 0;
	}
	$update['roe'] = $update['netincome'] / $update['totalequity'];
	if( (float)$update['roe'] >= 0.15 )
		$update['roeattractive'] = 1;
	else
		$update['roeattractive'] = 0;
                //ROA - net income / total assets - how well managemtn is using the company resources.
	$update['roa'] = $update['netincome'] / $update['totalasset'];
	if( $update['roa'] > 0.15 )
			$update['attractiveroa'] = 1;
	else
		$update['attractiveroa'] = 0;
                //ROA - net income / total assets - how well managemtn is using the company resources.
                //      Operating Margin = Operating profit/Net Sales
                //              As the management controls the operating expenses, this value tells how well management is doing
	$update['operatingmargin'] = $update['operatingincome'] / $update['revenue'];
                //lowcost operating margin > 10%
		if( (float)$update['operatingmargin'] >= 0.1 )
			$update['lowcost'] = 1;
		else
			$update['lowcost'] = 0;
                //ROCE (return on captial employed) = Net income/(Debt + shareholder equity)
	$update['roce'] = $update['netincome'] / ($update['totaldebt'] + $update['totalequity']);
	if( $update['roce'] > 0.15 )
		$update['attractiveroce'] = 1;
	else
		$update['attractiveroce'] = 0;
                //      Gross Profit Margin = Gross profit/Net Sales (revenue)
	$update['grossprofitmargin'] = $update['grossprofit'] / $update['revenue'];
	if( $update['grossprofitmargin'] > 0.25 )
		$update['attractivegross'] = 1;
	else
		$update['attractivegross'] = 0;
                //      Pretax Margin = pretax profit/net sales
	$update['pretaxmargin'] = $update['pretaxincome'] / $update['revenue'];
	if( $update['pretaxmargin'] > 0.20 )
		$update['attractivepretax'] = 1;
	else
		$update['attractivepretax'] = 0;
                //      Net Margin = Net Income/Net Sales
	$update['netmargin'] = $update['netincome'] / $update['revenue'];
	if( $update['netmargin'] > 0.15 )
		$update['attractivenet'] = 1;
	else
		$update['attractivenet'] = 0;
//! #152


	//var_dump( $update );
	
		return $update;
}	

function parse_file( $filename )
{
	$fp = fopen( $filename, "r" );
	if( $fp )
	{
		$data = "";
		while (!feof($fp)) {
       		    $data .= @fread($fp, 1024);
		}
	}
	fclose($fp);

	$companyname = getCompanyName( $data );
	$result = parse_data( $data );
	$result['corporatename'] = $companyname;
	$result['idstockinfo'] = $idstockinfo;
	return $result;
}


function getstatement( $stocksymbol, $exchange, $idstockinfo )
{
//googles pages sometimes sends extra crap that browsers handle no problem, but...
	$bad = array( "<span class=chr>", ",", "<b>" );
	$good = array( "", "", "" );
	$filename = googledownloadstatement( $stocksymbol, $exchange );
//var_dump( $data );
	//$data2 = $data;
	$result = parse_file( $filename );
	return $result;
}


/*
//TEST
$symbol = "BNI";
$exchange = "NYSE";
//$idstockinfo = 10;
$result = getstatement( $symbol, $exchange, $idstockinfo );
//var_dump( $result );
//	include_once( 'include_all.php' );
//	include_once( 'evalmarket.class.php' );
//	$market = new evalmarket();
//	$market->Insert( $result );
*/


?>


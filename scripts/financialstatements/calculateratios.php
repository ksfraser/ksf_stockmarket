<?php

function calculateratios( $update )
{

//20090606 KF
//Eventum issue #152
//RATIOS

		//debtratio     totaldebt/totalassets
	if( isset( $update['totalasset'] ))
	{
		$update['debtratio'] = $update['totaldebt'] / $update['totalasset'];
        	        //acceptabledebt netincome/revenue
		if( 	isset( $update['totalequity'] ) 
			&& $update['totalequity'] <> 0 
		)
			$update['roe'] = $update['netincome'] / $update['totalequity'];
		else
			$update['roe'] = 0;
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
	}
                //ROCE (return on captial employed) = Net income/(Debt + shareholder equity)
	if( isset( $update['totaldebt'] ) AND isset( $update['totalequity'] ) )
	{
		$update['roce'] = $update['netincome'] / ($update['totaldebt'] + $update['totalequity']);
		if( $update['roce'] > 0.15 )
			$update['attractiveroce'] = 1;
		else
			$update['attractiveroce'] = 0;
	}
	if( isset( $update['revenue'] ))
	{
		if( !isset( $update['netincome'] ) )
			$update['netincome'] = 0;
		if( !isset( $update['operatingincome'] ) )
			$update['operatingincome'] = 0;
		if( isset( $update['revenue'] ) &&  $update['revenue'] <> 0 )
			$update['acceptabledebtratio'] = $update['netincome'] / $update['revenue'];
		else
			$update['acceptabledebtratio'] = 0;
	                //roe  net_income/shareholder_equity - 15-20% is attractive investment
		if( $update['acceptabledebtratio'] > $update['debtratio'] )
		{
			$update['sustaindebtratio'] = 1;
		}
		else
		{
			$update['sustaindebtratio'] = 0;
		}
                //      Gross Profit Margin = Gross profit/Net Sales (revenue)
		if( isset( $update['revenue'] ) &&  $update['revenue'] <> 0 )
			$update['grossprofitmargin'] = $update['grossprofit'] / $update['revenue'];
		else
			$update['grossprofitmargin'] = 0;
		if( $update['grossprofitmargin'] > 0.25 )
			$update['attractivegross'] = 1;
		else
			$update['attractivegross'] = 0;
	                //      Pretax Margin = pretax profit/net sales
		if( isset( $update['revenue'] ) &&  $update['revenue'] <> 0 )
			$update['pretaxmargin'] = $update['pretaxincome'] / $update['revenue'];
		else
			$update['pretaxmargin'] = 0;
		if( $update['pretaxmargin'] > 0.20 )
			$update['attractivepretax'] = 1;
		else
			$update['attractivepretax'] = 0;
	                //      Net Margin = Net Income/Net Sales
		if( isset( $update['revenue'] ) &&  $update['revenue'] <> 0 )
			$update['netmargin'] = $update['netincome'] / $update['revenue'];
		else
			$update['netmargin'] = 0;
                //              As the management controls the operating expenses, this value tells how well management is doing
		if( isset( $update['revenue'] ) &&  $update['revenue'] <> 0 )
			$update['operatingmargin'] = $update['operatingincome'] / $update['revenue'];
		else
			$update['operatingmargin'] = 0;
        	        //lowcost operating margin > 10%
			if( (float)$update['operatingmargin'] >= 0.1 )
				$update['lowcost'] = 1;
			else
				$update['lowcost'] = 0;
	}
	if( 	isset( $update['netmargin'] ) 
		&& $update['netmargin'] > 0.15 )
		$update['attractivenet'] = 1;
	else
		$update['attractivenet'] = 0;
//! #152
	//var_dump( $update );
	return $update;
}	

?>

<?php

echo '<html><head></head>
	<frameset cols="10%,90%" border=0>
	<frame name="1" src="http://' . $_SERVER['SERVER_NAME'] . '/finance/controller/menu.php" />
	<frameset rows="75%,25%">
		<frame name="2" src="http://192.168.1.15/finance/model/portfolio.list.php" />
		<frame name="1" src="http://' . $_SERVER['SERVER_NAME'] . '/finance/controller/workflowmenu.php" />
	</frameset>
	<noframes>Why doesn\'t your browser handle frames?</noframes>
	</frameset>
<body>
	<p>This is outside the menu frame
</body></html>';
?>

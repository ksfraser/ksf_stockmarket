<html>
<head><title>Mail</title></head>
<body>
<table><tr><td>
<?php
$host='{localhost/notls/imap}INBOX'; //Host to connect
$host='{192.168.1.14/notls/nntp}finance'; //Host to connect
$user='kevin';
$pass='letmein';
$from='kevin@localhost'; //Mail to send from

$mail=@imap_open($host,$user,$pass) or die("Can't connect: " . imap_last_error());

if($_REQUEST['delete']) {
    $number=$_REQUEST['delete'];
    imap_delete($mail,$number);
    imap_expunge($mail);
}

if($_REQUEST['see']) {
    $number=$_REQUEST['see'];

    echo "<pre>";
    echo imap_body($mail,$number);
    echo "</pre><p>\n\n";
        
    echo "<a href='javascript:history.back()'>Back</a>";
    echo "<br><a href='page.php?delete=$number'>Delete</a>";
        
} else {
    if($_REQUEST['create']=="new") {
        if($_POST['send_m']) {
            $to=$_POST['to'];
            $subject=$_POST['title'];
            $message=$_POST['mail'];

            imap_mail($to,$subject,$message,"From: $from");
        }
        ?>
<form method=POST>
To: <input type="text" name="to"><br>
Title:<input type="text" name="title"><p>
Mail:<br>
<textarea name='mail'>
</textarea><p>
<input type="submit" name='send_m'  value='Po.lji'>
</form>
    <?php
    } else {
        $mails=imap_num_msg($mail);
        echo "<b>" . $from . "</b> : ";
        if($mails==0) {
            echo "<i>no mails.</i>";
        } else {        
            echo "$mails mails<p>";

            for($i=1;$i<=$mails;$i++) {
                $chead=imap_headerinfo($mail,$i);
                $mid=ltrim($chead->Msgno);
                    
                echo "<a href='page.php?see=$mid'>";

                echo $chead->subject;
                echo "</a>";
                echo "<br>\n";
            }
        }
        echo "<p><a href='page.php?create=new'>New mail</a><p>";
    }
}
imap_close($mail);
?>
</tr></td></table>
</body>
</html> 


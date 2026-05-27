<?php

function parse_line($input_text, $delimiter = ',', $text_qualifier = '"') {
    $text = trim($input_text);

    if(is_string($delimiter) && is_string($text_qualifier)) {
        $re_d = '\x' . dechex(ord($delimiter));            //format for regexp
        $re_tq = '\x' . dechex(ord($text_qualifier));    //format for regexp

        $fields = array();
        $field_num = 0;
        while(strlen($text) > 0) {
            if($text{0} == $text_qualifier) {
                preg_match('/^' . $re_tq . '((?:[^' . $re_tq . ']|(?<=\x5c)' . $re_tq . ')*)' . $re_tq . $re_d . '?(.*)$/', $text, $matches);

                $value = str_replace('\\' . $text_qualifier, $text_qualifier, $matches[1]);
                $text = trim($matches[2]);

                $fields[$field_num++] = $value;
            } else {
                preg_match('/^([^' . $re_d . ']*)' . $re_d . '?(.*)$/', $text, $matches);

                $value = $matches[1];
                $text = trim($matches[2]);

                $fields[$field_num++] = $value;
            }
        }

        return $fields;
    } else {
        return false;
    }
}



?>

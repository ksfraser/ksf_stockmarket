#! /bin/bash

# wiki_import.sh - mediawiki automatic file import script
#
# @Author:  Tong SUN, (c) 2006-2007
# @Release: $ $Revision: 1.21 $, under the BSD license
# @HomeURL: http://xpt.sourceforge.net/
#
# @Description: The script is designed to import a whole folder of     
#               files into mediawiki, with the folder directory tree   
#               mapped as wiki category hierarchy. The specification of
#               the file-to-import is passed from standard input.      
#

# {{{ LICENSE: 

# 
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted, provided
# that the above copyright notices appear in all copies and that both those
# copyright notices and this permission notice appear in supporting
# documentation, and that the names of author not be used in advertising or
# publicity pertaining to distribution of the software without specific,
# written prior permission.  Tong Sun makes no representations about the
# suitability of this software for any purpose.  It is provided "as is"
# without express or implied warranty.
#
# TONG SUN DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL ADOBE
# SYSTEMS INCORPORATED AND DIGITAL EQUIPMENT CORPORATION BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# 

# }}} 

# ############################################################## &cs ###
# ::::::::::::::::::::::::::::::::::::::::::::::::::::::::: Var Defs :::

# == Script Begin

#set -x

# ############################################################## &cs ###
# :::::::::::::::::::::::::::::::::::::::::::::::: Subroutines begin :::

fhelp(){
  cat $0.hlp
  exit 0
}

# {{{ wiki building functions: 

build_category_path(){
  fspec=$1;	shift
  fout=$1;	shift

  > "$fout"
  [ "$_opt_header" ] || return 

  > $ttf.cat
  catp=$(dirname "$fspec")
  while [ "$catp" != '.' ]; do
    catn=$(basename "$catp")
    echo "$catn" >> $ttf.cat
    catp=$(dirname "$catp")
  done

  $echo -n "[[:Category:$_opt_root]]/[[:Category:$_opt_sect]]" > "$fout"
  tac $ttf.cat | 
  while read catn; do 
    $echo -n "/[[:Category:$catn]]" >> "$fout"
  done
  $echo "\n----" >> "$fout"
}

build_header(){
  fspec=$1;	shift

  [ "$_opt_header" ] || return 

  fspec=`echo "$fspec" | sed 's|^\./||'`

  $echo "{{Import Disclaim}}\n----"
  [ "$_opt_link" ] && cat <<EOF
'''Original article'''
[http://$_opt_arch/`echo "$fspec" | sed 's/ /\%20/g'`]
----
EOF
  $echo "'''Extracted Content'''\n"
}

build_footer(){
  fspec=$1;	shift

  [ "$_opt_footer" ] || return 

  [ "$_opt_res" ] && echo "{{$_opt_res Restricted}}"
  $echo "[[Category:$(basename "$(dirname "$fspec")")]]\n----\n~~~~"
}

build_pre(){
  fspec=$1;	shift

  echo "<pre>"
  cat "$fspec"
  echo "</pre>"
}

build_empty(){
  echo "Content not extracted. Check above url instead."
}

build_oversized(){
  echo "Content oversized. Check above url instead."
}

build_doc(){
  fspec=$1;	shift

  antiword "$fspec"
}

build_txt(){
  fspec=$1;	shift

  cat "$fspec"
}

_to_html(){
  _fspec=$1;	shift
  fout=$1;	shift

  sed -r 's|(\xc2\|\xc3\|\x82\|\xa0\|\xa2)+| |g;' "$_fspec" > "$fout".t
  perl -MHTML::WikiConverter -e 'my $wc = new HTML::WikiConverter( dialect => 'MediaWiki' ); print $wc->html2wiki( file => "'"$fout".t'");'
}

build_htm(){
  _to_html "$@"
}

build_html(){
  _to_html "$@"
}

# the pdftohtml (from poppler-utils v0.5.1-2) is too buggy to produce
# anything uesful now. import the .pdf file without content extracting now.
build_pdf(){
  fspec=$1;	shift
  fout=$1;	shift

  pdftohtml -noframes -stdout "$fspec" > "$fout".h
  _to_html "$fout".h "$fout"
}

build_rtf(){
  fspec=$1;	shift
  fout=$1;	shift

  unrtf --html "$fspec" > "$fout".h
  _to_html "$fout".h "$fout"
}

build_xls(){
  fspec=$1;	shift
  fout=$1;	shift

  xlhtml -a -nc -nh "$fspec" > "$fout".h
  _to_html "$fout".h "$fout"
}

build_bat(){
  build_pre "$1"
}

wiki_convert(){
  fspec=$1;	shift
  fout=$1;	shift

  build_category_path "$fspec" "$fout"
  build_header "$fspec" >> "$fout"

  fsize=$(get_fsize  "$fspec")
  if [ "0$fsize" -gt $((_opt_max*2)) ]; then
    echo "-- File: '$fspec' content not extracted due to oversize ($fsize)." >&2
    build_oversized "$fspec" >> "$fout";
  else
    fext=$(echo "$fspec" | get_fext)
    case $fext in
    doc|txt) 
      echo "-- Importing $fext file: '$fspec'..." >&2
      build_$fext "$fspec" >> "$fout";;
    htm|html|rtf|xls) 
      echo "-- Importing $fext file: '$fspec'..." >&2
      build_$fext "$fspec" "$fout" >> "$fout";;
    asp|bat|cmd|cfg|inf|ini|pl|reg|sh|sql|vbs) 
      echo "-- Importing file '$fspec' as-is..." >&2
      build_pre "$fspec" >> "$fout";;
    bin|bmp|db|gif|jpg|maff|gz|tar.gz|tgz|vsd|zip|pdf) 
      echo "-- Importing '$fspec' as empty content file..." >&2
      build_empty "$fspec" >> "$fout";;
    *) 
      echo "-- Importing unknown .'$fspec' file as empty content file..." >&2
      build_empty "$fspec" >> "$fout";;
    esac
  fi

  build_footer "$fspec" >> "$fout"

  if [ "$_opt_debug" ]; then 
    echo "$fout"
  else
    fsize=$(get_fsize "$fout")
    if [ "0$fsize" -gt $((_opt_max-200)) ]; then
      echo "  Converted result: '$fout' skipped due to oversize ($fsize)." >&2
    else
      # use --title, otherwise, the file 'OS 7.3 update v1.doc' will
      # be imported with title 'OS 7' by importTextFile.php
      $_opt_php --title "$(echo "$fspec" | get_fname)" --user $_opt_user "$fout"
      rm "$fout"*
    fi
  fi
}

# }}} 

# ============================================================== &ss ===

# {{{ support functions: 

# get file name
get_fname(){
  sed -e 's,^.*/,,; s,\.\([^\.]*\)$,,'
}

# get file extension
get_fext(){
  sed 's/^.*\.//; y/ABCDEFGHIJKLMNOPQRSTUVWXYZ/abcdefghijklmnopqrstuvwxyz/;'
}

# get file size
get_fsize(){
  ls -l "$1" | awk '{ print $5}'
}

# }}} 

# -------------------------------------------------------------- &ss ---

# ############################################################## &cs ###
# :::::::::::::::::::::::::::::::::::::::::::::::: Main script begin :::

[ ${1+T} ] || fhelp

# sourcing init & CLP scripts
. $0.ini
. $0.clp

if [ "$_opt_check_failed" ]; then 
  echo "Not all mandatory options are set."
  fhelp
fi

[ ${1+T} ] && {
  echo "Extra parameter: '$1'."
  fhelp
}

while read fspec; do 
  fout=$ttd/"$(echo "$fspec" | get_fname)".txt
  wiki_convert "$fspec" "$fout"
done

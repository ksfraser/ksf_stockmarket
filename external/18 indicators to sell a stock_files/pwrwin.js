
function powerstats(strURL,txtBox)
{
  symbol = ""
  co = ""
   if(txtBox!="")
   {
      obj = eval('document.powerOptForm1234.' + txtBox)
      symbol = '&txtSymbol=' + obj.value
      co = '&co=' + document.powerOptForm1234.pwrCompany5678.value
   }
   else
      co = '?co=' + document.powerOptForm1234.pwrCompany5678.value
   w = 750
   h = 600
   l = 10
   if (self.screen)
   {     // for NN4 and IE4
      scrW = screen.width;
      scrH = screen.height;
      l = (scrW - w) / 2
   }
   
   t = 5

  powerWin = window.open('http:\/\/www.poweropt.com/' + strURL + symbol + co,"new","left=" + l + ",top=" + t + ",height=" + h + ",width=" + w + ",toolbar,location,status,resizable,scrollbars")
}

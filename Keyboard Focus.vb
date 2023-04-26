do while true

'API XML
   dim xml as string = API.XML()
   dim x as new system.xml.xmldocument
   x.loadxml(xml)

'Current Selected Preview Source
   dim WhatIsOnPreview as String = (x.SelectSingleNode("/vmix/preview").InnerText)

'Central 2 Router
   dim Central2 as WebRequest= WebRequest.Create("http://192.168.100.186:8080/?cmd=router&subcmd=info&name=Keyboard Focus")
   dim responseCentral2 As WebResponse = Central2.GetResponse()

'Central 2
   'Debug.Print(CType(responseCentral2, HttpWebResponse).StatusDescription)
   Dim dataStream As Stream = responseCentral2.GetResponseStream()
   Dim reader As New StreamReader(dataStream)
   Dim responseFromCentral2 As String = reader.ReadToEnd()
   'console.writeline(responseFromCentral2)

'Central Responses
   dim kbdP100 as String = responseFromCentral2.Contains("BIRDDOG-P100(CAM)")
   dim kbdP200 as String = responseFromCentral2.Contains("BIRDDOG-P200(CAM)")
   dim kbdP4K as String = responseFromCentral2.Contains("BIRDDOG-P4K(CAM)")

If WhatIsOnPreview = "4" And Not kbdP100 = True Then

   dim client as WebRequest= WebRequest.Create("http://192.168.100.186:8080/?cmd=router&subcmd=sconnect&hname=P100&format=CAM&name=Keyboard%20Focus")
   dim response As WebResponse = client.GetResponse()
   response.Close
   sleep(500)

else If WhatIsOnPreview = "17" And Not kbdP200 = True Then
   dim client as WebRequest= WebRequest.Create("http://192.168.100.186:8080/?cmd=router&subcmd=sconnect&hname=BIRDDOG-P200&format=CAM&name=Keyboard%20Focus")
   dim response As WebResponse = client.GetResponse()
   response.Close
   sleep(500)

else If WhatIsOnPreview = "11" And Not kbdP4K = True Then
   dim client as WebRequest= WebRequest.Create("http://192.168.100.186:8080/?cmd=router&subcmd=sconnect&hname=BIRDDOG-P4K&format=CAM&name=Keyboard%20Focus")
   dim response As WebResponse = client.GetResponse()
   response.Close
End if


sleep(500)
loop







'If responseFromCentral2.Contains("BIRDDOG-P200(CAM)") = True Then
'console.writeline("The string Contains() 'P200' ")
'Else
'console.writeline("The String does not Contains() 'P200'")
'End If
'console.writeline(kbdP200)






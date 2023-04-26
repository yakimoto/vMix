'PTZ Keyboard Focus
    'Written by: Jake Fineman (BirdDogJake)
    'Goal: When selecting a PTZ Source for Preview, automatically change the BirdDog PTZ Keyboard to the selected PTZ Camera, for instant control on the keyboard.
    'How: 
        '1. Change Central 2 virtual Router selected Source by checking vMix Preview and Current Router Source
        '2. PTZ Keyboard is Subscribbed to the NDI Router created by Central 2
    'Logic: If PTZ Camera is selected for Preview but NOT Central Router > Change Central Router to selected Camera
    'Requirements: BirdDog Central 2.0 and BirdDog PTZ Keyboard

do while true

'API XML
   dim xml as string = API.XML()
   dim x   as new system.xml.xmldocument
   x.loadxml(xml)

'Current Selected Preview Source
   dim WhatIsOnPreview as String = (x.SelectSingleNode("/vmix/preview").InnerText)

'Central 2 Router
   dim Central2               as WebRequest  = WebRequest.Create("http://192.168.100.167:8080/?cmd=router&subcmd=info&name=Keyboard Focus")
   dim responseCentral2       as WebResponse = Central2.GetResponse()
   dim dataStreamCentral2     as Stream      = responseCentral2.GetResponseStream()
   dim readerCentral2         as New           StreamReader(dataStreamCentral2)
   dim readerResponseCentral2 as String      = readerCentral2.ReadToEnd()

'Central Responses
   dim kbdP100 as String = readerResponseCentral2.Contains("BIRDDOG-P100(CAM)")
   dim kbdP200 as String = readerResponseCentral2.Contains("BIRDDOG-P200(CAM)")
   dim kbdP4K  as String = readerResponseCentral2.Contains("BIRDDOG-P4K(CAM)")

If WhatIsOnPreview = "4" And Not kbdP100 = True Then
   dim client   as WebRequest  = WebRequest.Create("http://192.168.100.167:8080/?cmd=router&subcmd=sconnect&hname=BIRDDOG-P100&format=CAM&name=Keyboard%20Focus")
   dim response as WebResponse = client.GetResponse()

else If WhatIsOnPreview = "5" And Not kbdP200 = True Then
   dim client   as WebRequest  = WebRequest.Create("http://192.168.100.167:8080/?cmd=router&subcmd=sconnect&hname=BIRDDOG-P200&format=CAM&name=Keyboard%20Focus")
   dim response as WebResponse = client.GetResponse()

else If WhatIsOnPreview = "6" And Not kbdP4K = True Then
   dim client   as WebRequest  = WebRequest.Create("http://192.168.100.167:8080/?cmd=router&subcmd=sconnect&hname=BIRDDOG-P4K&format=CAM&name=Keyboard%20Focus")
   dim response as WebResponse = client.GetResponse()

End if

sleep(1000)
loop


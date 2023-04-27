' Constants
Const PTZ_KEYBOARD_IP As String = "192.168.100.167"
Const ROUTER_INFO_COMMAND As String = "/?cmd=router&subcmd=info&name=Keyboard Focus"
Const ROUTER_CONNECT_COMMAND_FORMAT As String = "/?cmd=router&subcmd=sconnect&hname={0}&format=CAM&name=Keyboard%20Focus"

Public Async Sub Main()
    ' Check that the vMix API is available before starting
    While Not IsAPIAvailable()
        Await Task.Delay(1000)
    End While

    ' Main loop
    Do While True
        Try
            ' Get the current state of vMix through the API
            Dim xml As String = API.XML()
            Dim xmlDoc As New System.Xml.XmlDocument()
            xmlDoc.LoadXml(xml)

            ' Get the name of the source currently on preview
            Dim previewSource As String = xmlDoc.SelectSingleNode("/vmix/preview").InnerText

            ' Get the current state of the PTZ Keyboard router
            Dim routerResponseString As String = Await GetRouterInfoAsync()

            ' Check if each PTZ keyboard is connected to the router
            Dim keyboardP100 As Boolean = IsKeyboardConnected(routerResponseString, "BIRDDOG-P100(CAM)")
            Dim keyboardP200 As Boolean = IsKeyboardConnected(routerResponseString, "BIRDDOG-P200(CAM)")
            Dim keyboardP4K As Boolean = IsKeyboardConnected(routerResponseString, "BIRDDOG-P4K(CAM)")

            ' Connect the router to the selected PTZ camera if it's not already connected
            Dim routerConnectCommand As String = GetRouterConnectCommand(previewSource, keyboardP100, keyboardP200, keyboardP4K)

            ' Send the command to connect the router to the selected PTZ camera
            Await ConnectRouterToCameraAsync(routerConnectCommand)

        Catch ex As Exception
            ' Handle any errors that occur during the loop
            Debug.WriteLine("Error in main loop: " & ex.Message)
        End Try

        ' Wait for a short period of time before checking the API again
        Await Task.Delay(1000)
    Loop
End Sub

Private Function IsAPIAvailable() As Boolean
    ' Check that the vMix API is available before starting
    Dim apiRequest As WebRequest = WebRequest.Create("http://localhost:8088/api/")
    Dim apiResponse As WebResponse = Nothing

    Try
        apiResponse = apiRequest.GetResponse()
    Catch ex As Exception
        Return False
    End Try

    Return True
End Function

Private Async Function GetRouterInfoAsync() As Task(Of String)
' Get the current state of the PTZ Keyboard router
Dim routerResponseString As String = ""

Dim routerRequest As WebRequest = WebRequest.Create("http://" & PTZ_KEYBOARD_IP & ROUTER_INFO_COMMAND)

' Send the request and handle any errors
Try
    Dim routerResponse As WebResponse = Await routerRequest.GetResponseAsync()
    Dim routerDataStream As Stream = routerResponse.GetResponseStream()

    If Not routerDataStream Is Nothing Then
        Using routerReader = New StreamReader(routerDataStream)
            routerResponseString = Await routerReader.ReadToEndAsync()
        End Using
    End If

    ' Check if the router response indicates that it is connected
    Dim routerJson As JObject = JObject.Parse(routerResponseString)
    Dim routerStatus As String = routerJson("status").ToString()

    If routerStatus = "Connected" Then
        Debug.WriteLine("PTZ Keyboard router is connected.")
    Else
        Debug.WriteLine("PTZ Keyboard router is not connected.")
    End If

Catch ex As Exception
    ' Handle any errors that occur during the web request
    ' For example, log the error or display a message to the user
    Debug.WriteLine("Error getting router info: " & ex.Message)
End Try

Return routerResponseString
End Function

Private Function IsKeyboardConnected(routerResponseString As String, keyboardModel As String) As Boolean
' Parse the response from the router and check if the specified keyboard is connected
Dim routerJson As JObject = JObject.Parse(routerResponseString)
Dim routerData As JToken = routerJson("data")

For Each device In routerData
    If device("model").ToString() = keyboardModel And device("status").ToString() = "Connected" Then
        Return True
    End If
Next

Return False
End Function

Private Function GetRouterConnectCommand(previewSource As String, keyboardP100 As Boolean, keyboardP200 As Boolean, keyboardP4K As Boolean) As String
' Determine the PTZ camera that should be connected to the router based on the preview source
Dim cameraModel As String = ""

Select Case previewSource
    Case "PTZ1"
        cameraModel = "BIRDDOG-P200(CAM)"
    Case "PTZ2"
        cameraModel = "BIRDDOG-P100(CAM)"
    Case "PTZ3"
        cameraModel = "BIRDDOG-P4K(CAM)"
    Case Else
        Return ""
End Select

' Determine which PTZ keyboard(s) should be connected to the camera
Dim keyboardList As New List(Of String)

If keyboardP100 And cameraModel <> "BIRDDOG-P100(CAM)" Then
    keyboardList.Add("BIRDDOG-P100(CAM)")
End If

If keyboardP200 And cameraModel <> "BIRDDOG-P200(CAM)" Then
    keyboardList.Add("BIRDDOG-P200(CAM)")
End If

If keyboardP4K And cameraModel <> "BIRDDOG-P4K(CAM)" Then
    keyboardList.Add("BIRDDOG-P4K(CAM)")
End If

' Generate the command to connect the router to the camera and keyboard(s)
Dim connectCommand As String = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, cameraModel)

If keyboardList.Count > 0 Then
    Dim keyboardString As String = String.Join(",", keyboardList)
    connectCommand &= "&devs=" & keyboardString
End If

Return connectCommand
End Function

Private Async Function ConnectRouterToCameraAsync(connectCommand As String) As Task
' Send the command to connect the router to the selected PTZ camera
Dim routerRequest As WebRequest = WebRequest.Create("http://" & PTZ_KEYBOARD_IP & connectCommand)

' Send the request and handle any errors
Try
    Dim routerResponse As WebResponse = Await routerRequest.GetResponseAsync()
    Dim routerDataStream As Stream = routerResponse.GetResponseStream()

    If Not routerDataStream Is Nothing Then
        Using routerReader = New StreamReader(routerDataStream)
            Dim routerResponseString As String = Await routerReader.ReadToEndAsync()
            Debug.WriteLine("Router response: " & routerResponseString)
        End Using
    End If
Catch ex As Exception
    ' Handle any errors that occur during the web request
    ' For example, log the error or display a message to the user
    Debug.WriteLine("Error connecting router to camera: " & ex.Message)
End Try
End Function

End Module

'This code defines a VB.NET module that automatically switches the input of a PTZ camera based on the currently selected input in vMix. The module uses the vMix API to determine the currently selected input, and then sends a command to a PTZ keyboard router to switch the input of the connected PTZ camera. The module is designed to run continuously in the background, and will check the state of vMix and the PTZ keyboard router every second.

'The module defines several functions:

'- `IsAPIAvailable`: checks if the vMix API is available by sending a request to the API endpoint.
'- `GetRouterInfoAsync`: sends a request to the PTZ keyboard router to get its current state, and returns the response as a string.
'- `IsKeyboardConnected`: parses the response from the PTZ keyboard router to determine if a specified keyboard is connected.
'- `GetRouterConnectCommand`: generates a command to connect the PTZ keyboard router to a specified PTZ camera based on the currently selected input in vMix.
'- `ConnectRouterToCameraAsync`: sends a command to the PTZ keyboard router to connect it to a specified PTZ camera and keyboard.

'The `Main` subroutine is the entry point for the module, and contains the main loop that runs continuously in the background. The loop checks the state of vMix and the PTZ keyboard router every second, and switches the input of the connected PTZ camera if necessary.

'The module uses several constants to define the IP address of the PTZ keyboard router, the commands to send to the router to get its current state and connect it to a PTZ camera, and the names of the PTZ keyboards and cameras to use. The module also uses the `Newtonsoft.Json` library to parse JSON responses from the PTZ keyboard router.

'Note that this module is specific to the PTZ keyboard router and PTZ cameras used in the example, and may need to be modified to work with different equipment. Additionally, this module assumes that the PTZ keyboard router is connected to the same network as the computer running vMix. If the router is on a different network, additional configuration may be required to allow communication between the computer and the router.
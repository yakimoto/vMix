' Constants
Const PTZ_KEYBOARD_IP As String = "192.168.100.167"
Const ROUTER_INFO_COMMAND As String = "/?cmd=router&subcmd=info&name=Keyboard Focus"
Const ROUTER_CONNECT_COMMAND_FORMAT As String = "/?cmd=router&subcmd=sconnect&hname={0}&format=CAM&name=Keyboard%20Focus"

Public Sub Main()
    ' Check that the vMix API is available before starting
    While Not IsAPIAvailable()
        Thread.Sleep(1000)
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
            Dim routerResponseString As String = GetRouterInfo()

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
        Thread.Sleep(1000)
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

Private Function GetRouterInfo() As String
    ' Get the current state of the PTZ Keyboard router
    Dim routerResponseString As String = ""

    Dim routerRequest As WebRequest = WebRequest.Create("http://" & PTZ_KEYBOARD_IP & ROUTER_INFO_COMMAND)

    ' Send the request and handle any errors
    Try
        Dim routerResponse As WebResponse = routerRequest.GetResponse()
        Dim routerDataStream As Stream = routerResponse.GetResponseStream()

        If Not routerDataStream Is Nothing Then
            Using routerReader = New StreamReader(routerDataStream)
                routerResponseString = routerReader.ReadToEnd()
            End Using
        End If
    Catch ex As Exception
        ' Handle any errors that occur during the web request
        ' For example, log the error or display a message to the user
        Debug.WriteLine("Error getting router info: " & ex.Message)
    End Try

    Return routerResponseString
End Function

Private Function IsKeyboardConnected(routerResponseString As String, keyboardModel As String) As Boolean
    ' Check if a specific PTZ keyboard is connected to the router
    Return Not String.IsNullOrWhiteSpace(routerResponseString) AndAlso routerResponseString.Contains(keyboardModel)
End Function

Private Function GetRouterConnectCommand(previewSource As String, keyboardP100 As Boolean, keyboardP200 As Boolean, keyboardP4K As Boolean) As String
    ' Connect the router to the selected PTZ camera if it's not already connected
    Dim routerConnectCommand As String = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "")

Select Case previewSource
    Case "PTZ 1"
        If keyboardP100 Then
            routerConnectCommand = ""
        ElseIf keyboardP200 Then
            routerConnectCommand = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "BIRDDOG-P100(CAM)")
        ElseIf keyboardP4K Then
            routerConnectCommand = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "BIRDDOG-P200(CAM)")
        End If
    Case "PTZ 2"
        If keyboardP200 Then
            routerConnectCommand = ""
        ElseIf keyboardP100 Then
            routerConnectCommand = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "BIRDDOG-P200(CAM)")
        ElseIf keyboardP4K Then
            routerConnectCommand = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "BIRDDOG-P100(CAM)")
        End If
    Case "PTZ 3"
        If keyboardP4K Then
            routerConnectCommand = ""
        ElseIf keyboardP100 Then
            routerConnectCommand = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "BIRDDOG-P4K(CAM)")
        ElseIf keyboardP200 Then
            routerConnectCommand = String.Format(ROUTER_CONNECT_COMMAND_FORMAT, "BIRDDOG-P4K(CAM)")
        End If
End Select

Return routerConnectCommand
End Function

Private Async Function ConnectRouterToCamera(routerConnectCommand As String) As Task
    ' Connect the router to the selected PTZ camera if it's not already connected
    If String.IsNullOrWhiteSpace(routerConnectCommand) Then
        Return
    End If

    Dim routerConnectRequest As WebRequest = WebRequest.Create("http://" & PTZ_KEYBOARD_IP & routerConnectCommand)

    ' Send the request asynchronously and handle any errors
    Try
        Dim routerConnectResponse As WebResponse = Await routerConnectRequest.GetResponseAsync()
        Dim routerConnectDataStream As Stream = routerConnectResponse.GetResponseStream()

        If Not routerConnectDataStream Is Nothing Then
            Using routerConnectReader = New StreamReader(routerConnectDataStream)
                Dim routerConnectResponseString = routerConnectReader.ReadToEnd()

                ' Check the response string for errors and handle them appropriately
                If routerConnectResponseString.Contains("ERROR") Then
                    Debug.WriteLine("Error connecting router to camera: " & routerConnectResponseString)
                End If
            End Using
        End If
    Catch ex As Exception
        ' Handle any errors that occur during the web request
        ' For example, log the error or display a message to the user
        Debug.WriteLine("Error connecting router to camera: " & ex.Message)
    End Try
End Sub

End Module
import cv2
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_ndi
from dash.dependencies import Input, Output
from flask import Response
from base64 import b64encode

app = dash.Dash(__name__)

ndi_send = dash_ndi.NDISend("My NDI Switcher Output", ["My NDI Switcher Group"])

@app.callback(Output("ndi-sources", "children"), [Input("interval", "n_intervals")])
def update_sources(n_intervals):
    ndi_instance = dash_ndi.NDI()
    ndi_instance.connect()
    sources = ndi_instance.get_sources()
    return [html.Button(source, id=f"ndi-source-{source}") for source in sources]

@app.callback(Output("ndi-preview", "src"), [Input(f"ndi-source-{source}", "n_clicks") for source in dash_ndi.NDI().get_sources()])
def switch_source(*args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    source_name = ctx.triggered[0]["prop_id"].split("-")[-1]
    dash_ndi.NDI().switch_source(source_name)
    return f"/ndi-video/{source_name}"

@app.server.route("/ndi-video/<source_name>")
def serve_ndi_video(source_name):
    def generate():
        ndi_receiver = dash_ndi.NDIReceiver(source_name)
        while True:
            try:
                frame = ndi_receiver.recv()
                if frame is None:
                    continue
                image = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                _, jpeg = cv2.imencode(".jpg", image)
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
            except Exception as e:
                print(f"Error receiving NDI video: {e}")
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.callback(Output("ndi-video-preview", "src"), [Input("ndi-preview", "src")])
def update_preview(src):
    return src

@app.callback(Output("ndi-video", "src"), [Input("interval", "n_intervals")])
def update_video(n_intervals):
    try:
        _, jpeg = cv2.imencode(".jpg", ndi_send.recv())
        return f"data:image/jpeg;base64,{b64encode(jpeg.tobytes()).decode('utf-8')}"
    except Exception as e:
        print(f"Error updating NDI video: {e}")
        return ""


app.layout = html.Div(
    [
        html.H1("NDI Switcher"),
        html.Div(
            [
                html.Div(
                    [
                        html.H3("NDI Sources"),
                        html.Div(id="ndi-sources"),
                    ],
                    style={"width": "30%", "float": "left"},
                ),
                html.Div(
                    [
                        html.H3("NDI Preview"),
                        html.Img(id="ndi-preview", style={"max-width": "100%"}),
                        html.H3("NDI Video"),
                        html.Img(id="ndi-video-preview", style={"max-width": "100%"}),
                    ],
                    style={"width": "70%", "float": "left"},
                ),
            ],
            style={"clear": "both"},
        ),
        dcc.Interval(id="interval", interval=1000),
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)

import React, { useState, useEffect } from "react";
import NDI from "ndi";
import NDISend from "ndi-send";
import NDIReceiver from "ndi-receiver";

async function createImageBitmapFromFrame(frame) {
  const imageData = await createImageBitmap(frame.getImageData());
  return imageData;
}

async function initializeNDI() {
  try {
    // Create a new NDI instance and connect to the NDI router
    const ndiInstance = new NDI();
    await ndiInstance.connect();

    // Create a new NDISend instance and start sending NDI output
    const ndiSendInstance = new NDISend({
      name: "My NDI Switcher Output",
      groups: ["My NDI Switcher Group"],
    });
    await ndiSendInstance.start();

    // Get the list of NDI sources
    const sources = await ndiInstance.getSources();

    return { ndiInstance, ndiSendInstance, sources };
  } catch (error) {
    console.error("Failed to initialize NDI:", error);
    // TODO: Handle error
    return null;
  }
}

function NDISource({ source, ndiSend }) {
  const [imageBitmap, setImageBitmap] = useState(null);

  function handleVideo(frame) {
    createImageBitmapFromFrame(frame).then((newImageBitmap) => {
      setImageBitmap(newImageBitmap);
      ndiSend.send({
        data: frame.data.buffer,
        width: frame.width,
        height: frame.height,
        fourCC: frame.fourCC,
      });
    });
  }

  function handleError(error) {
    console.error(`Failed to start NDI receiver for ${source}:`, error);
    // TODO: Handle error
  }

  return (
    <div>
      <video
        id={source}
        autoPlay
        width={320}
        height={240}
        srcObject={imageBitmap}
      />
      <NDIReceiver
        key={source}
        source={source}
        onVideo={handleVideo}
        onError={handleError}
      />
    </div>
  );
}

function NDISwitcher({ ndiInstance, ndiSendInstance, sources }) {
  const [previewQuality, setPreviewQuality] = useState("medium");

  function switchSource(sourceName) {
    ndiInstance.switchSource(sourceName);
  }

  function handlePreviewQualityChange(e) {
    if (ndiSendInstance) {
      setPreviewQuality(e.target.value);
    }
  }

  const previewWidth = previewQuality === "low" ? 320 : 640;
  const previewHeight = previewQuality === "low" ? 240 : 480;

  return (
    <div>
      <div>
        <label htmlFor="previewQuality">Preview Quality:</label>
        <select id="previewQuality" onChange={handlePreviewQualityChange}>
          <option value="low">Low</option>
          <option value="medium" selected>
            Medium
          </option>
          <option value="high">High</option>
        </select>
      </div>
      <div>
        {sources.map((source) => (
          <button key={source} onClick={() => switchSource(source)}>
            {source}
          </button>
        ))}
      </div>
      <div>
        {sources.map((source) => (
          <NDISource
            key={source}
            source={source}
            ndiSend={ndiSendInstance}
          />
        ))}
      </div>
      <video
        id="preview"
        autoPlay
        width={previewWidth}
        height={previewHeight}
      >
        <NDIReceiver
  source={null}
  onVideo={(frame) => {
    const canvas = document.createElement("canvas");
    canvas.width = previewWidth;
    canvas.height = previewHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(frame.getImage(), 0, 0, previewWidth, previewHeight);
    const imageData = ctx.getImageData(0, 0, previewWidth, previewHeight);
    ndiSendInstance.send({
      data: imageData.data.buffer,
      width: imageData.width,
      height: imageData.height,
      fourCC: "BGRA",
    });
  }}
  onError={(error) => {
    console.error("Failed to receive NDI preview:", error);
    // TODO: Handle error
  }}
/>
</video>
</div>
);

function App() {
  const [ndiInitialized, setNdiInitialized] = useState(false);
  const [ndiInstance, setNdiInstance] = useState(null);
  const [ndiSendInstance, setNdiSendInstance] = useState(null);
  const [sources, setSources] = useState([]);

  useEffect(() => {
    async function initNDI() {
      const ndiData = await initializeNDI();
      if (ndiData) {
        setNdiInstance(ndiData.ndiInstance);
        setNdiSendInstance(ndiData.ndiSendInstance);
        setSources(ndiData.sources);
        setNdiInitialized(true);
      }
    }
    initNDI();
  }, []);

  return (
    <div>
      {ndiInitialized ? (
        <NDISwitcher
          ndiInstance={ndiInstance}
          ndiSendInstance={ndiSendInstance}
          sources={sources}
        />
      ) : (
        <p>Initializing NDI...</p>
      )}
    </div>
  );
}

export default App;

"use client";
import { useState, useEffect } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";

export default function Home() {
  const [services, setServices] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [voice, setVoice] = useState("en-US-Neural2-C");
  const [encoding, setEncoding] = useState("MP3");
  const [audioUrl, setAudioUrl] = useState("");

  useEffect(() => {
    fetch(`${apiBase}/apis`).then(r => r.json()).then(d => setServices(d.services || [])).catch(() => setServices([]));
  }, []);

  const runTts = async () => {
    let headers: any = {"Content-Type": "application/json"};
    if (process.env.NEXT_PUBLIC_AUTH_MODE === "hmac") {
      const ct = await fetch(`${apiBase}/client-token`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({path: "/tts/synthesize", method: "POST"})
      }).then(r => r.json());
      headers["x-ts"] = ct.ts;
      headers["x-sig"] = ct.sig;
    } else {
      const token = await (window as any).auth?.currentUser?.getIdToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    const resp = await fetch(`${apiBase}/tts/synthesize`, {
      method: "POST",
      headers,
      body: JSON.stringify({text, voice, encoding})
    });
    const blob = await resp.blob();
    setAudioUrl(URL.createObjectURL(blob));
  };

  return (
    <div style={{display: "flex", padding: 20}}>
      <div style={{width: "30%"}}>
        <h3>Enabled APIs</h3>
        <ul>
          {services.map(s => <li key={s}>{s}</li>)}
        </ul>
      </div>
      <div style={{flex: 1}}>
        <h3>Text To Speech</h3>
        <textarea value={text} onChange={e => setText(e.target.value)} rows={4} style={{width: "100%"}} />
        <div>
          <label>Voice: </label>
          <input value={voice} onChange={e => setVoice(e.target.value)} />
        </div>
        <div>
          <label>Encoding: </label>
          <input value={encoding} onChange={e => setEncoding(e.target.value)} />
        </div>
        <button onClick={runTts}>Run</button>
        {audioUrl && <div><audio controls src={audioUrl}></audio><a download="tts.mp3" href={audioUrl}>Download</a></div>}
        <h4>Add Function</h4>
        <p>Placeholder</p>
      </div>
    </div>
  );
}

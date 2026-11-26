import { useState } from "react";
import CreateCampaign from "./pages/CreateCampaign";
import Editor from "./pages/Editor";

export default function App() {
  const [tab, setTab] = useState<"create" | "editor">("create");
  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Adrobot</h1>
      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={() => setTab("create")} disabled={tab === "create"}>
          Create
        </button>
        <button onClick={() => setTab("editor")} disabled={tab === "editor"}>
          Editor
        </button>
      </nav>
      {tab === "create" ? <CreateCampaign /> : <Editor />}
    </div>
  );
}

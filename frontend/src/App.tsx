import { useState } from "react";
import CreateCampaign from "./pages/CreateCampaign";
import Editor from "./pages/Editor";
import { Button } from "@/components/ui/button";

export default function App() {
  const [tab, setTab] = useState<"create" | "editor">("create");
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">Adrobot</h1>
      <nav className="flex gap-2 mb-6 border-b border-slate-200 pb-2">
        <Button
          variant={tab === "create" ? "default" : "ghost"}
          onClick={() => setTab("create")}
          disabled={tab === "create"}
        >
          Create
        </Button>
        <Button
          variant={tab === "editor" ? "default" : "ghost"}
          onClick={() => setTab("editor")}
          disabled={tab === "editor"}
        >
          Editor
        </Button>
      </nav>
      {tab === "create" ? <CreateCampaign /> : <Editor />}
    </div>
  );
}

import { useState } from "react";
import CreateCampaign from "./pages/CreateCampaign";
import Editor from "./pages/Editor";
import { Button } from "@/components/ui/button";

export default function App() {
  const [tab, setTab] = useState<"create" | "editor">("create");
  return (
    <div className="max-w-4xl mx-auto px-4 py-4">
      <header className="flex items-center gap-4 mb-4 border-b border-slate-200 pb-2">
        <h1 className="text-xl font-bold text-slate-900">Adrobot</h1>
        <nav className="flex gap-2">
          <Button
            size="sm"
            variant={tab === "create" ? "default" : "ghost"}
            onClick={() => setTab("create")}
            disabled={tab === "create"}
          >
            Create
          </Button>
          <Button
            size="sm"
            variant={tab === "editor" ? "default" : "ghost"}
            onClick={() => setTab("editor")}
            disabled={tab === "editor"}
          >
            Editor
          </Button>
        </nav>
      </header>
      {tab === "create" ? <CreateCampaign /> : <Editor />}
    </div>
  );
}

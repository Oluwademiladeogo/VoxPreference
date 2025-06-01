import { useState } from "react";
import Chat from "./components/Chat";
import Sidebar from "./components/Sidebar";

function App() {
  const [activeView, setActiveView] = useState<"chat">("chat");

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar activeView={activeView} onSelect={setActiveView} />
      <main className="flex-1 overflow-hidden">
        <div className="h-full">
          <Chat />
        </div>
      </main>
    </div>
  );
}

export default App;

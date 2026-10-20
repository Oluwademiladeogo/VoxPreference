import { useState } from "react";
import Chat from "./components/Chat";
import PGAnalysis from "./components/PGAnalysis";
import Sidebar, { View } from "./components/Sidebar";

function App() {
  const [activeView, setActiveView] = useState<View>("pg");

  return (
    <div className="flex flex-col md:flex-row h-screen bg-gray-100">
      <Sidebar activeView={activeView} onSelect={setActiveView} />
      <main className="flex-1 min-h-0 overflow-hidden">
        {/* Both views stay mounted so a long analysis survives a switch to the legacy view */}
        <div className={activeView === "chat" ? "h-full" : "hidden"}>
          <Chat />
        </div>
        <div className={activeView === "pg" ? "h-full" : "hidden"}>
          <PGAnalysis />
        </div>
      </main>
    </div>
  );
}

export default App;

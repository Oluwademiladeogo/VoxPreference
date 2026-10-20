export type View = "chat" | "pg";

interface SidebarProps {
  onSelect: (view: View) => void;
  activeView: View;
}

const Sidebar = ({ onSelect, activeView }: SidebarProps) => {
  const buttonClass = (view: View) =>
    `flex-1 md:w-full p-3 rounded-lg flex items-center justify-center md:justify-start space-x-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
      activeView === view
        ? "bg-blue-600 text-white"
        : "text-gray-300 hover:bg-gray-700"
    }`;

  return (
    <div className="w-full md:w-64 shrink-0 bg-gray-800 text-white md:h-screen p-4">
      <div className="mb-4 md:mb-8">
        <h1 className="text-2xl font-bold">VoxPreference</h1>
        <p className="text-gray-400 text-sm">Audio Preference Assistant</p>
      </div>

      <nav className="flex gap-2 md:block md:space-y-2">
        <button
          onClick={() => onSelect("pg")}
          aria-current={activeView === "pg" ? "page" : undefined}
          className={buttonClass("pg")}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
            />
          </svg>
          <span>PG analysis</span>
        </button>
        <button
          onClick={() => onSelect("chat")}
          aria-current={activeView === "chat" ? "page" : undefined}
          className={buttonClass("chat")}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <span>Transcription (legacy)</span>
        </button>
      </nav>
    </div>
  );
};

export default Sidebar;

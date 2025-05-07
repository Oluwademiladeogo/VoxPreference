interface SidebarProps {
  onSelect: (view: "chat") => void;
  activeView: "chat";
}

const Sidebar = ({ onSelect, activeView }: SidebarProps) => {
  return (
    <div className="w-64 bg-gray-800 text-white h-screen p-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">VoxPreference</h1>
        <p className="text-gray-400 text-sm">Audio Preference Assistant</p>
      </div>

      <nav className="space-y-2">
        <button
          onClick={() => onSelect("chat")}
          className={`w-full p-3 rounded-lg flex items-center space-x-2 transition-colors ${
            activeView === "chat"
              ? "bg-blue-600 text-white"
              : "text-gray-300 hover:bg-gray-700"
          }`}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <span>Chat</span>
        </button>
      </nav>
    </div>
  );
};

export default Sidebar;

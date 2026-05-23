export default function ResearchTabs({
  activeTab,
  setActiveTab,
}) {
  const tabs = [
    "report",
    "critic",
    "sources",
    "logs",
  ];

  return (
    <div className="flex gap-4 mt-10">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() =>
            setActiveTab(tab)
          }
          className={`px-5 py-3 rounded-2xl capitalize transition-all
          ${
            activeTab === tab
              ? "bg-blue-600 text-white"
              : "bg-white border border-slate-200"
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
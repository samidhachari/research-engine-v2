import { Search } from "lucide-react";

export default function SearchBar({
  query,
  setQuery,
  mode,
  setMode,
  onSearch,
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-[32px] p-5 shadow-2xl mt-14">
      <div className="flex items-center gap-4">
        <Search className="text-slate-400" />

        <input
          type="text"
          value={query}
          onChange={(e) =>
            setQuery(e.target.value)
          }
          placeholder="Research quantum security, AGI, semiconductors..."
          className="w-full outline-none bg-transparent text-lg"
        />

        <button
          onClick={onSearch}
          className="bg-blue-600 text-white px-8 py-4 rounded-2xl shadow-lg"
        >
          Generate
        </button>
      </div>

      <div className="flex gap-3 mt-5">
        {["quick", "research", "deep"].map(
          (item) => (
            <button
              key={item}
              onClick={() =>
                setMode(item)
              }
              className={`px-5 py-3 rounded-2xl capitalize transition-all
              ${
                mode === item
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {item}
            </button>
          )
        )}
      </div>
    </div>
  );
}
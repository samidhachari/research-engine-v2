export default function SourceExplorer({
  sources,
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-[32px] p-8 shadow-xl">
      <h2 className="text-2xl font-bold mb-6">
        Source Explorer
      </h2>

      <div className="space-y-4">
        {sources?.map((source, idx) => (
          <div
            key={idx}
            className="border border-slate-200 rounded-2xl p-4 hover:shadow-lg transition-all"
          >
            <div className="flex justify-between">
              <h3 className="font-semibold text-slate-900">
                {source.title}
              </h3>

              <span className="text-blue-600 font-medium">
                Trust {source.trust_score}
              </span>
            </div>

            <p className="text-sm text-slate-500 mt-2">
              {source.url}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
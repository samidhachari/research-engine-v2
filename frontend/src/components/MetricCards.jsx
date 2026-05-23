import {
  FileText,
  BrainCircuit,
  ShieldCheck,
  Activity,
} from "lucide-react";

const metrics = [
  {
    title: "Sources",
    value: "142",
    icon: FileText,
  },
  {
    title: "Academic Papers",
    value: "61",
    icon: BrainCircuit,
  },
  {
    title: "Trust Score",
    value: "94%",
    icon: ShieldCheck,
  },
  {
    title: "Latency",
    value: "2m 14s",
    icon: Activity,
  },
];

export default function MetricCards() {
  return (
    <div className="grid md:grid-cols-4 gap-6 mt-10">
      {metrics.map((metric, idx) => {
        const Icon = metric.icon;

        return (
          <div
            key={idx}
            className="bg-white border border-slate-200 rounded-[28px] p-6 shadow-lg"
          >
            <div className="flex justify-between items-center">
              <div>
                <p className="text-slate-500 text-sm">
                  {metric.title}
                </p>

                <h2 className="text-3xl font-bold mt-2">
                  {metric.value}
                </h2>
              </div>

              <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center">
                <Icon className="text-blue-600" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
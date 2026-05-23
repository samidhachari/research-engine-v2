import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

const stages = [
  "Query Planning",
  "Scholar Search",
  "Arxiv Retrieval",
  "PDF Intelligence",
  "Evidence Ranking",
  "Report Generation",
  "Critic Analysis",
];

export default function PipelineProgress({
  loading,
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-[32px] p-8 shadow-xl mt-12">
      <h2 className="text-2xl font-bold mb-8">
        Research Pipeline
      </h2>

      <div className="grid md:grid-cols-4 gap-5">
        {stages.map((stage, idx) => (
          <motion.div
            key={idx}
            animate={
              loading
                ? {
                    scale: [1, 1.05, 1],
                  }
                : {}
            }
            transition={{
              repeat: Infinity,
              duration: 1.8,
              delay: idx * 0.2,
            }}
            className="bg-slate-50 rounded-3xl p-5 border border-slate-200"
          >
            <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center mb-4">
              <Sparkles className="text-blue-600" />
            </div>

            <h3 className="font-semibold">
              {stage}
            </h3>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
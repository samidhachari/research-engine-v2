import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export default function Navbar() {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-between items-center px-10 py-6"
    >
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg">
          <Sparkles className="text-white" />
        </div>

        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            AskLumen Research
          </h1>

          <p className="text-slate-500 text-sm">
            AI-native Research Engine
          </p>
        </div>
      </div>

      <button className="bg-white border border-slate-200 px-5 py-3 rounded-2xl shadow-lg hover:scale-105 transition-all">
        Enterprise
      </button>
    </motion.nav>
  );
}
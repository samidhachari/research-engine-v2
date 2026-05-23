import { motion } from "framer-motion";

export default function HeroSection() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 60 }}
      animate={{ opacity: 1, y: 0 }}
      className="text-center mt-16"
    >
      <h1 className="text-6xl font-bold text-slate-900 leading-tight">
        Research Like an
        <span className="text-blue-600">
          {" "}
          Intelligence Engine
        </span>
      </h1>

      <p className="mt-6 text-xl text-slate-500 max-w-3xl mx-auto leading-relaxed">
        Deep research powered by academic retrieval,
        evidence grounding, PDF intelligence and
        multi-agent reasoning.
      </p>
    </motion.div>
  );
}
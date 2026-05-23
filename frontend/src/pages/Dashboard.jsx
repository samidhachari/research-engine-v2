// import { useState } from "react";

// import Navbar from "../components/Navbar";
// import HeroSection from "../components/HeroSection";
// import SearchBar from "../components/SearchBar";
// import PipelineProgress from "../components/PipelineProgress";
// import ResearchTabs from "../components/ResearchTabs";
// import SourceExplorer from "../components/SourceExplorer";
// import UploadPDF from "../components/UploadPDF";
// import MetricCards from "../components/MetricCards";

// import { generateResearch } from "../services/api";

// export default function Dashboard() {
//   const [query, setQuery] = useState("");
//   const [mode, setMode] = useState("deep");

//   const [loading, setLoading] =
//     useState(false);

//   const [activeTab, setActiveTab] =
//     useState("report");

//   const [report, setReport] =
//     useState("");

//   const [sources, setSources] =
//     useState([]);

//   const runResearch = async () => {
//     try {
//       setLoading(true);

//       const result =
//         await generateResearch(
//           query,
//           mode
//         );

//       setReport(result.report);

//       setSources(
//         result.source_explorer || []
//       );

//       setLoading(false);
//     } catch (err) {
//       console.error(err);

//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-screen bg-[#F8FBFF] overflow-hidden relative">
//       <div className="absolute top-[-200px] left-[-200px] w-[500px] h-[500px] rounded-full bg-blue-200 blur-[120px] opacity-40" />

//       <div className="absolute bottom-[-200px] right-[-200px] w-[500px] h-[500px] rounded-full bg-sky-200 blur-[120px] opacity-40" />

//       <Navbar />

//       <main className="max-w-7xl mx-auto px-8 pb-20">
//         <HeroSection />

//         <SearchBar
//           query={query}
//           setQuery={setQuery}
//           mode={mode}
//           setMode={setMode}
//           onSearch={runResearch}
//         />

//         <MetricCards />

//         <PipelineProgress
//           loading={loading}
//         />

//         <UploadPDF />

//         <ResearchTabs
//           activeTab={activeTab}
//           setActiveTab={setActiveTab}
//         />

//         <div className="grid lg:grid-cols-3 gap-8 mt-10">
//           <div className="lg:col-span-2 bg-white rounded-[32px] border border-slate-200 p-8 shadow-xl">
//             <h2 className="text-2xl font-bold mb-6">
//               Research Report
//             </h2>

//             <div className="prose max-w-none">
//               {report || (
//                 <p className="text-slate-500">
//                   Your generated research
//                   report will appear here.
//                 </p>
//               )}
//             </div>
//           </div>

//           <SourceExplorer
//             sources={sources}
//           />
//         </div>
//       </main>
//     </div>
//   );
// }

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import SearchBar from "../components/SearchBar";
import UploadPDF from "../components/UploadPDF";
import SourceExplorer from "../components/SourceExplorer";
import MetricCards from "../components/MetricCards";
import PipelineProgress from "../components/PipelineProgress";
import { generateResearch } from "../services/api";
import { useState } from "react";

export default function Dashboard() {
  const [query, setQuery] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [report, setReport] =
    useState("");

  const [sources, setSources] =
    useState([]);

  const runResearch = async (
    mode = "quick"
  ) => {
    try {
      setLoading(true);

      const res =
        await generateResearch(
          query,
          mode
        );

      setReport(
        res.report || ""
      );

      setSources(
        res.sources || []
      );
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#F6F8FC]">

      <div className="max-w-[1600px] mx-auto px-8 py-10">

        {/* top search */}
        <motion.div
          initial={{
            opacity: 0,
            y: 30,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
        >
          <SearchBar
            query={query}
            setQuery={setQuery}
            runResearch={
              runResearch
            }
          />
        </motion.div>

        {/* upload */}
        <div className="mt-8">
          <UploadPDF />
        </div>

        {/* metrics */}
        {report && (
          <div className="mt-8">
            <MetricCards />
          </div>
        )}

        {/* loading */}
        {loading && (
          <div className="mt-8">
            <PipelineProgress />
          </div>
        )}

        {/* main layout */}
        {report && (
          <div className="grid grid-cols-12 gap-8 mt-10">

            {/* report */}
            <motion.div
              initial={{
                opacity: 0,
                y: 20,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              className="
                col-span-8
                bg-white
                rounded-[32px]
                shadow-sm
                border
                border-slate-200
                p-10
                h-[85vh]
                overflow-y-auto
              "
            >
              <h2 className="text-4xl font-bold mb-8 text-slate-900">
                Research Report
              </h2>

              <article
                className="
                  prose
                  prose-slate
                  max-w-none
                  prose-headings:font-bold
                  prose-p:text-slate-700
                  prose-p:leading-8
                  prose-li:leading-8
                  prose-h2:text-3xl
                  prose-h3:text-2xl
                "
              >
                <ReactMarkdown>
                  {report}
                </ReactMarkdown>
              </article>
            </motion.div>

            {/* sources */}
            <motion.div
              initial={{
                opacity: 0,
                x: 30,
              }}
              animate={{
                opacity: 1,
                x: 0,
              }}
              className="
                col-span-4
                sticky
                top-10
                h-[85vh]
                overflow-hidden
              "
            >
              <SourceExplorer
                sources={
                  sources
                }
              />
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
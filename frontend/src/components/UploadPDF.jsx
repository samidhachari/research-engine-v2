import { Upload } from "lucide-react";

export default function UploadPDF() {
  return (
    <div className="mt-10 border-2 border-dashed border-slate-300 bg-white rounded-[32px] p-10 text-center shadow-lg">
      <Upload
        className="mx-auto text-blue-600"
        size={50}
      />

      <h2 className="text-2xl font-bold mt-4">
        Upload 100+ PDFs
      </h2>

      <p className="text-slate-500 mt-2">
        Drag and drop academic papers,
        patents, research documents.
      </p>

      <button className="mt-6 bg-blue-600 text-white px-6 py-4 rounded-2xl shadow-lg">
        Select PDFs
      </button>
    </div>
  );
}
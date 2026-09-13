import { FolderOpen, RefreshCw, Settings } from 'lucide-react';

function DirectoryField({ label, value, onChange, onChoose, placeholder }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <div className="flex rounded-md shadow-sm">
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="flex-1 block w-full min-w-0 rounded-l-md text-sm border border-slate-300 px-3 py-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          placeholder={placeholder}
        />
        <button type="button" onClick={onChoose} title="Open File Explorer" className="px-3 border-y border-slate-300 bg-slate-50 text-slate-600 hover:bg-slate-100">
          <FolderOpen className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default function ConfigurationPanel({ sourceDirectory, setSourceDirectory, outputDirectory, setOutputDirectory, chooseDirectory, clearSavedDirectories, scanDirectory, isScanning }) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
        <Settings className="w-5 h-5 text-slate-500" />
        Source Configuration
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DirectoryField label="Shared Drive Directory" value={sourceDirectory} onChange={setSourceDirectory} onChoose={() => chooseDirectory(setSourceDirectory)} placeholder="Folder chứa 4 file CSV" />
        <DirectoryField label="Local Conversion Directory" value={outputDirectory} onChange={setOutputDirectory} onChoose={() => chooseDirectory(setOutputDirectory)} placeholder="Nơi lưu Parquet tạm thời" />
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <button type="button" onClick={clearSavedDirectories} className="text-sm text-slate-500 hover:text-red-600">
          Clear saved folders
        </button>
        <button type="button" onClick={scanDirectory} disabled={isScanning} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
          {isScanning ? 'Scanning...' : "Scan Today's Files"}
        </button>
      </div>
    </section>
  );
}

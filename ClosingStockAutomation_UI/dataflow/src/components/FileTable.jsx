import { Fragment } from 'react';
import { FileText, FolderOpen, Play, Square } from 'lucide-react';
import { getStatusConfig } from '../utils/status';
import ProgressBar from './ProgressBar';
import CheckPanel from './CheckPanel';

export default function FileTable({ filteredFiles, handleSelectAll, handleSelectFile, startConversion, stopConversion, onCheck, checkedFile, onCloseCheck }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider">
            <th className="px-6 py-4 font-medium w-12"><input type="checkbox" className="rounded border-slate-300 text-blue-600 w-4 h-4" onChange={handleSelectAll} checked={filteredFiles.length > 0 && filteredFiles.every((file) => file.selected || file.status === 'missing')} /></th>
            <th className="px-6 py-4 font-medium min-w-[270px]">File Details</th>
            <th className="px-6 py-4 font-medium min-w-[180px]">Date Modified</th>
            <th className="px-6 py-4 font-medium w-32">Status</th>
            <th className="px-6 py-4 font-medium min-w-[200px]">Progress</th>
            <th className="px-6 py-4 font-medium text-right w-24">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {filteredFiles.length === 0 ? (
            <tr><td colSpan="6" className="px-6 py-12 text-center text-slate-500"><FolderOpen className="w-12 h-12 mx-auto text-slate-300 mb-3" /><p>Chưa scan thư mục nguồn.</p></td></tr>
          ) : filteredFiles.map((file) => {
            const statusCfg = getStatusConfig(file.status);
            return (
              <Fragment key={file.id}>
              <tr key={file.id} className={`hover:bg-slate-50/80 transition-colors ${file.selected ? 'bg-blue-50/30' : ''}`}>
                <td className="px-6 py-4"><input type="checkbox" disabled={file.status === 'missing'} className="rounded border-slate-300 text-blue-600 w-4 h-4" checked={file.selected} onChange={() => handleSelectFile(file.id)} /></td>
                <td className="px-6 py-4"><div className="flex items-start gap-3"><FileText className={`w-5 h-5 mt-0.5 ${statusCfg.color}`} /><div><p className={`text-sm font-bold truncate max-w-[270px] ${statusCfg.color}`} title={file.name}>{file.name}</p><div className="flex items-center gap-3 mt-1 text-xs text-slate-500 font-medium"><span>{file.size_label || '-'}</span><span>{file.profile || '-'}</span></div></div></div></td>
                <td className="px-6 py-4 text-xs text-slate-600 whitespace-nowrap">{file.date_modified || '-'}</td>
                <td className="px-6 py-4"><div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${statusCfg.bg} ${statusCfg.color}`}>{statusCfg.icon}{statusCfg.text}</div></td>
                <td className="px-6 py-4"><ProgressBar progress={file.progress} status={file.status} />{file.log.length > 0 && <p className="text-[10px] text-slate-400 mt-1 truncate max-w-[200px]" title={file.log[file.log.length - 1]}>{file.log[file.log.length - 1]}</p>}</td>
                <td className="px-6 py-4 text-right"><div className="flex items-center justify-end gap-2">{file.status === 'completed' && <button onClick={() => onCheck(file.id)} className="px-2.5 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded hover:bg-indigo-100" title="Check conversion">Check</button>}{file.status === 'missing' ? null : file.status === 'converting' ? <button onClick={() => stopConversion(file.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded" title="Stop"><Square className="w-5 h-5" /></button> : <button onClick={() => startConversion(file.id)} disabled={file.status === 'completed'} className="p-1.5 text-slate-400 hover:text-blue-600 rounded disabled:text-slate-300" title="Run file"><Play className="w-5 h-5" /></button>}</div></td>
              </tr>
              {checkedFile?.id === file.id && (
                <tr key={`${file.id}-check`} className="bg-slate-50">
                  <td colSpan="6" className="p-3 sm:p-5">
                    <CheckPanel file={checkedFile} onClose={onCloseCheck} />
                  </td>
                </tr>
              )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

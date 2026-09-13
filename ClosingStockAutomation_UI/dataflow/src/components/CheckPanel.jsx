import {
  Check,
  CheckCircle2,
  Columns3,
  Database,
  FileArchive,
  FileText,
  HardDrive,
  Rows3,
  Timer,
  X,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';

function formatValue(value) {
  return value === null || value === undefined ? '-' : value.toLocaleString?.() ?? value;
}

function MetricCard({ icon: Icon, label, value, detail, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  };
  return (
    <div className={`rounded-xl border p-3 ${tones[tone]}`}>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide opacity-75">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="mt-2 text-xl font-bold">{value}</div>
      {detail && <div className="mt-1 text-[11px] opacity-70">{detail}</div>}
    </div>
  );
}

function MatchMetric({ label, csvValue, parquetValue, format = formatValue }) {
  const match = csvValue === parquetValue;
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 border-b border-slate-100 py-2.5 last:border-0">
      <div><span className="block text-[10px] uppercase text-slate-400">CSV</span><strong className="text-sm text-slate-700">{format(csvValue)}</strong></div>
      <div className={`rounded-full p-1 ${match ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`} title={match ? 'Match' : 'Mismatch'}>
        {match ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
      </div>
      <div className="text-right"><span className="block text-[10px] uppercase text-slate-400">Parquet</span><strong className={`text-sm ${match ? 'text-emerald-700' : 'text-red-700'}`}>{format(parquetValue)}</strong></div>
      <span className="col-span-3 text-[11px] font-medium text-slate-500">{label}</span>
    </div>
  );
}

function columnLabel(index) {
  let value = '';
  let current = index + 1;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    value = String.fromCharCode(65 + remainder) + value;
    current = Math.floor((current - 1) / 26);
  }
  return value;
}

function preparePreview(rows, schema) {
  const firstRow = rows?.[0] || [];
  const headerNames = ['date', 'store_id', 'product_id', 'category', 'qty_sold', 'revenue', 'discount', 'currency'];
  const hasBusinessHeader = headerNames.every((name, index) => String(firstRow[index] || '').trim().toLowerCase() === name);
  if (hasBusinessHeader) {
    return {
      rows: rows.slice(1),
      schema: headerNames.map((name) => ({ name })),
    };
  }
  return { rows, schema };
}

function PreviewTable({ rows, schema }) {
  if (!rows?.length) return <p className="py-6 text-center text-xs text-slate-500">No preview data.</p>;
  const columnCount = Math.max(schema?.length || 0, ...rows.map((row) => row.length));
  const headers = schema?.length ? schema.map((column) => column.name) : Array.from({ length: columnCount }, (_, index) => `column${index + 1}`);
  return (
    <div className="max-h-[420px] overflow-auto rounded-lg border border-slate-200">
      <table className="min-w-full border-collapse text-left text-xs">
        <thead className="sticky top-0 z-[1] text-[10px] uppercase tracking-wide text-slate-500">
          <tr className="bg-slate-800 text-slate-300"><th className="sticky left-0 z-[2] w-10 border-r border-slate-600 bg-slate-800 px-2 py-1" />{headers.map((header, index) => <th key={`letter-${index}`} className="min-w-[140px] border-r border-slate-600 px-3 py-1 text-center font-semibold">{columnLabel(index)}</th>)}</tr>
          <tr className="bg-slate-100"><th className="sticky left-0 z-[2] border-r border-slate-200 bg-slate-100 px-2 py-2 text-center">#</th>{headers.map((header, index) => <th key={`${header}-${index}`} className="min-w-[140px] border-r border-slate-200 px-3 py-2 text-left normal-case">{header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => <tr key={rowIndex} className="border-t border-slate-100 odd:bg-white even:bg-slate-50"><td className="sticky left-0 border-r border-slate-200 bg-slate-100 px-2 py-2 text-center font-semibold text-slate-500">{rowIndex + 2}</td>{Array.from({ length: columnCount }, (_, columnIndex) => <td key={columnIndex} className="max-w-[220px] whitespace-nowrap border-r border-slate-100 px-3 py-2 text-slate-700" title={row[columnIndex] == null ? '' : String(row[columnIndex])}>{row[columnIndex] == null ? '' : String(row[columnIndex])}</td>)}</tr>)}
        </tbody>
      </table>
      </div>
  );
}

function comparable(value) {
  if (value === null || value === undefined) return '';
  const text = String(value).trim();
  const numeric = Number(text);
  return text !== '' && Number.isFinite(numeric) ? String(numeric) : text;
}

function PreviewDifference({ csvRows, parquetRows }) {
  const rowCount = Math.max(csvRows?.length || 0, parquetRows?.length || 0);
  const mismatchRows = Array.from({ length: rowCount }, (_, rowIndex) => {
    const csvRow = csvRows?.[rowIndex] || [];
    const parquetRow = parquetRows?.[rowIndex] || [];
    return csvRow.length !== parquetRow.length || csvRow.some((value, index) => comparable(value) !== comparable(parquetRow[index]));
  }).filter(Boolean).length;
  return <div className={`mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${mismatchRows ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>{mismatchRows ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}{mismatchRows ? `${mismatchRows} preview row(s) differ` : 'All preview rows match'}</div>;
}

export default function CheckPanel({ file, onClose }) {
  const [tab, setTab] = useState('check');
  const check = file?.check;
  const csv = check?.csv;
  const parquet = check?.parquet;
  const compression = check?.compression_ratio ?? 0;
  const compressionTone = compression > 0 ? 'green' : 'amber';
  const csvPreview = preparePreview(csv?.preview, parquet?.schema);
  const parquetPreview = preparePreview(parquet?.preview, parquet?.schema);

  return (
    <aside className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3">
        <div className="min-w-0"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-indigo-600">Conversion review</p><h2 className="mt-1 truncate text-sm font-bold text-slate-900" title={file?.name}>{file?.name}</h2></div>
        <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-white hover:text-slate-700" title="Close review"><X className="h-5 w-5" /></button>
      </div>
      <div className="flex border-b border-slate-200 px-3 pt-2">
        <button onClick={() => setTab('check')} className={`flex items-center gap-1 border-b-2 px-3 py-2 text-xs font-bold ${tab === 'check' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'}`}><Check className="h-4 w-4" />Check</button>
        <button onClick={() => setTab('preview')} className={`flex items-center gap-1 border-b-2 px-3 py-2 text-xs font-bold ${tab === 'preview' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'}`}><Database className="h-4 w-4" />Sample data</button>
      </div>

      <div className="space-y-4 p-4">
        {tab === 'check' ? <>
          <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2.5 text-xs text-emerald-700"><CheckCircle2 className="h-5 w-5 shrink-0" /><span>Conversion completed in <strong>{check?.elapsed_seconds ?? '-'} seconds</strong></span></div>
          <div><h3 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-700"><FileArchive className="h-4 w-4 text-indigo-500" />File metadata</h3><div className="grid grid-cols-2 gap-2"><MetricCard icon={Rows3} label="Rows" value={formatValue(parquet?.rows)} detail="CSV and Parquet" tone="blue" /><MetricCard icon={Columns3} label="Columns" value={formatValue(parquet?.columns)} detail="Stored in Parquet" tone="blue" /><MetricCard icon={HardDrive} label="CSV size" value={csv?.size_label || '-'} detail="Source file" /><MetricCard icon={FileArchive} label="Parquet size" value={parquet?.size_label || '-'} detail="Compressed output" tone={compressionTone} /></div></div>
          <div className="rounded-xl border border-slate-200 p-3"><div className="flex items-center justify-between"><h3 className="text-xs font-bold uppercase tracking-wide text-slate-700">Compression</h3><strong className={`text-sm ${compression > 0 ? 'text-emerald-700' : 'text-amber-700'}`}>{compression > 0 ? `Reduced ${compression}%` : 'No reduction'}</strong></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${Math.min(Math.max(compression, 0), 100)}%` }} /></div><p className="mt-2 text-[11px] text-slate-500">CSV: {csv?.size_label || '-'} <span className="px-1">-&gt;</span> Parquet: {parquet?.size_label || '-'}</p></div>
          <div className="rounded-xl border border-slate-200 p-3"><h3 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-700"><CheckCircle2 className="h-4 w-4 text-indigo-500" />Integrity check</h3><MatchMetric label="Total rows" csvValue={csv?.rows} parquetValue={parquet?.rows} /><MatchMetric label="Total columns" csvValue={csv?.columns} parquetValue={parquet?.columns} /></div>
          <div className="rounded-xl border border-slate-200 p-3"><h3 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-700"><Columns3 className="h-4 w-4 text-indigo-500" />Parquet schema</h3><div className="max-h-48 overflow-auto rounded-lg border border-slate-100"><table className="min-w-full text-left text-xs"><thead className="sticky top-0 bg-slate-50 text-[10px] uppercase text-slate-400"><tr><th className="px-3 py-2">Column</th><th className="px-3 py-2">Stored type</th></tr></thead><tbody>{(parquet?.schema || []).map((column) => <tr key={column.name} className="border-t border-slate-100"><td className="px-3 py-2 font-medium text-slate-700">{column.name}</td><td className="px-3 py-2 font-mono text-indigo-700">{column.type}</td></tr>)}</tbody></table></div></div>
          <div className="space-y-1 text-[10px] text-slate-400"><p className="flex items-start gap-1"><FileText className="mt-0.5 h-3 w-3 shrink-0" />CSV: {file?.path}</p><p className="flex items-start gap-1"><FileArchive className="mt-0.5 h-3 w-3 shrink-0" />Parquet: {check?.output}</p></div>
        </> : <>
          <div><h3 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-700"><Database className="h-4 w-4 text-indigo-500" />Sample data</h3><p className="mb-3 text-[11px] text-slate-500">Excel-style preview with column letters and row numbers. Values are separated into their own columns.</p><PreviewDifference csvRows={csvPreview.rows} parquetRows={parquetPreview.rows} /><div className="grid grid-cols-1 gap-4 2xl:grid-cols-2"><div className="min-w-0"><h4 className="mb-2 flex items-center gap-2 text-xs font-bold text-slate-700"><FileText className="h-4 w-4 text-indigo-500" />CSV source</h4><PreviewTable rows={csvPreview.rows} schema={csvPreview.schema} /></div><div className="min-w-0"><h4 className="mb-2 flex items-center gap-2 text-xs font-bold text-slate-700"><FileArchive className="h-4 w-4 text-emerald-500" />Parquet output</h4><PreviewTable rows={parquetPreview.rows} schema={parquetPreview.schema} /></div></div></div>
        </>}
      </div>
    </aside>
  );
}

import React, { ReactNode } from 'react';

export function Card({ children, className = '' }: { children: ReactNode, className?: string }) {
  return (
    <div className={`bg-ink-900 border border-ink-800 rounded-2xl p-4 ${className}`}>
      {children}
    </div>
  );
}

export function StatCard({ title, value, className = '' }: { title: string, value: string | number, className?: string }) {
  return (
    <Card className={`flex flex-col gap-2 ${className}`}>
      <span className="text-sm text-gray-400">{title}</span>
      <span className="text-2xl font-bold">{value}</span>
    </Card>
  );
}

export function Pill({ children, className = '' }: { children: ReactNode, className?: string }) {
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full bg-ink-800 border border-ink-700 ${className}`}>
      {children}
    </span>
  );
}

export function Button({ children, className = '', variant = 'primary', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) {
  const base = "px-4 py-2 rounded-xl font-medium transition-colors";
  const primary = "bg-cyan-500 hover:bg-cyan-600 text-white";
  const secondary = "bg-ink-800 hover:bg-ink-700 text-white border border-ink-700";
  const vClass = variant === 'primary' ? primary : secondary;
  return (
    <button className={`${base} ${vClass} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function Input({ className = '', ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input 
      className={`bg-ink-900 border border-ink-800 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-cyan-500 ${className}`} 
      {...props} 
    />
  );
}

export function Select({ className = '', children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select 
      className={`bg-ink-900 border border-ink-800 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-cyan-500 ${className}`} 
      {...props}
    >
      {children}
    </select>
  );
}

export function DataTable({ columns, data }: { columns: string[], data: React.ReactNode[][] }) {
  return (
    <div className="w-full overflow-x-auto rounded-2xl border border-ink-800">
      <table className="w-full text-left text-sm text-gray-300">
        <thead className="bg-ink-900 text-xs uppercase text-gray-400">
          <tr>
            {columns.map((c, i) => <th key={i} className="px-4 py-3">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-ink-800 hover:bg-ink-900/50">
              {row.map((cell, j) => <td key={j} className="px-4 py-3">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EmptyState({ message = "Not built yet" }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center w-full h-48 border border-dashed border-ink-700 rounded-2xl bg-ink-900/20 text-gray-400">
      <p>{message}</p>
    </div>
  );
}

export function Loading() {
  return (
    <div className="flex items-center justify-center w-full h-full p-8">
      <div className="w-8 h-8 border-4 border-ink-700 border-t-cyan-500 rounded-full animate-spin"></div>
    </div>
  );
}

export function PageHeader({ title, description }: { title: string, description?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-white">{title}</h1>
      {description && <p className="text-gray-400 text-sm mt-1">{description}</p>}
    </div>
  );
}

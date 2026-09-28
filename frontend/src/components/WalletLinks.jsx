import { useState } from "react";

function AddressRow({ address }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard?.writeText(address).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  };

  return (
    <button
      onClick={copy}
      className="w-full flex items-center justify-between px-3 py-1.5 rounded-md hover:bg-slate-800/60 text-left group"
      title="Click to copy"
    >
      <span className="font-mono text-xs text-slate-300 truncate">{address}</span>
      <span className="text-[10px] text-slate-600 group-hover:text-slate-400 shrink-0 ml-2">
        {copied ? "copied" : "copy"}
      </span>
    </button>
  );
}

export default function WalletLinks({ addresses, totalCount }) {
  const truncatedCount = totalCount - addresses.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-slate-500">
          {totalCount} linked address{totalCount === 1 ? "" : "es"} in this cluster
          <span className="text-slate-600"> · multi-input heuristic</span>
        </p>
      </div>
      <div className="max-h-56 overflow-y-auto rounded-lg border border-slate-800 divide-y divide-slate-800/60">
        {addresses.map((a) => (
          <AddressRow key={a} address={a} />
        ))}
      </div>
      {truncatedCount > 0 && (
        <p className="text-[11px] text-slate-600 mt-1.5">
          +{truncatedCount} more not shown (payload capped for display)
        </p>
      )}
    </div>
  );
}

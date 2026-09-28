export default function Timeline({ items }) {
  if (!items?.length) {
    return <p className="text-sm text-slate-500">No transaction activity recorded.</p>;
  }

  return (
    <div className="max-h-72 overflow-y-auto pr-2">
      <ol className="relative border-l border-slate-800 ml-2">
        {items.map((tx, i) => (
          <li key={tx.txid + i} className="mb-4 ml-4">
            <span className="absolute -left-1.5 w-2.5 h-2.5 rounded-full bg-emerald-500 mt-1.5" />
            <div className="flex items-center justify-between">
              <p className="text-xs font-mono text-slate-300">{tx.txid}</p>
              <p className="text-xs text-slate-500">{tx.timestamp}</p>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              fee {Number(tx.fee).toFixed(6)}
              {tx.src_ip && <> · ip {tx.src_ip}</>}
              {tx.asn && <> · {tx.asn}</>}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}

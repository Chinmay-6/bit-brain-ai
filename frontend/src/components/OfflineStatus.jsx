export default function OfflineStatus() {
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
      <span className="relative flex h-2 w-2">
        <span className="animate-pulse-slow absolute inline-flex h-full w-full rounded-full bg-risk-low opacity-60" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-risk-low" />
      </span>
      LOCAL · NO EXTERNAL NETWORK
    </div>
  );
}

export function RichContent({ content }: { content: string }) {
  const lines = content.split("\n").filter(Boolean);

  return (
    <div className="space-y-4 text-base leading-8 text-slate-700">
      {lines.map((line, index) => {
        if (line.startsWith("### ")) {
          return (
            <h3 key={`${line}-${index}`} className="pt-2 text-xl font-semibold text-slate-900">
              {line.replace("### ", "")}
            </h3>
          );
        }

        if (line.startsWith("## ")) {
          return (
            <h2 key={`${line}-${index}`} className="pt-4 text-2xl font-semibold text-slate-900">
              {line.replace("## ", "")}
            </h2>
          );
        }

        if (line.startsWith("- ")) {
          return (
            <div key={`${line}-${index}`} className="flex gap-3">
              <span className="mt-2 h-2 w-2 rounded-full bg-[#d0a46d]" />
              <span>{line.replace("- ", "")}</span>
            </div>
          );
        }

        return (
          <p key={`${line}-${index}`} className="text-base leading-8 text-slate-700">
            {line}
          </p>
        );
      })}
    </div>
  );
}

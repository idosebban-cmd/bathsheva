import { inlineSegments } from "../standardParts";

/** Renders the inline markdown used in standard-parts/*.md (bold, code, links). Links open in a new tab. */
export default function Md({ text }: { text: string }) {
  return (
    <>
      {inlineSegments(text).map((s, i) =>
        s.kind === "bold" ? (
          <strong key={i}>{s.text}</strong>
        ) : s.kind === "code" ? (
          <code key={i}>{s.text}</code>
        ) : s.kind === "link" ? (
          <a key={i} href={s.url} target="_blank" rel="noreferrer">
            {s.text}
          </a>
        ) : (
          <span key={i}>{s.text}</span>
        ),
      )}
    </>
  );
}

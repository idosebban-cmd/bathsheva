// Date and time formatting for display: UK local time (GMT/BST), day/month/year, 24-hour clock.
const UK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** "06/10/2026 14:52" in UK local time. Timestamps without a zone are treated as UTC (as the API stores them). */
export function ukDateTime(iso: string): string {
  const withZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(withZone);
  if (Number.isNaN(d.getTime())) return "";
  const parts = Object.fromEntries(UK.formatToParts(d).map((p) => [p.type, p.value]));
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}`;
}

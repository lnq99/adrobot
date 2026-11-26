import countries from "i18n-iso-countries";
import en from "i18n-iso-countries/langs/en.json";

countries.registerLocale(en);
const ALL = Object.entries(countries.getNames("en")) as [string, string][];

export default function CountrySelect({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    /* Native <select multiple> preserved for E2E: role="listbox" */
    <select
      multiple
      value={value}
      onChange={(e) =>
        onChange(Array.from(e.target.selectedOptions, (o) => o.value))
      }
      className="w-full min-h-[140px] rounded-md border border-slate-200 bg-white px-2 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {ALL.map(([code, name]) => (
        <option key={code} value={code}>
          {code} — {name}
        </option>
      ))}
    </select>
  );
}

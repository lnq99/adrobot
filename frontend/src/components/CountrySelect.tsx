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
    <select
      multiple
      value={value}
      onChange={(e) =>
        onChange(Array.from(e.target.selectedOptions, (o) => o.value))
      }
      style={{ minWidth: 220, minHeight: 140 }}
    >
      {ALL.map(([code, name]) => (
        <option key={code} value={code}>
          {code} — {name}
        </option>
      ))}
    </select>
  );
}

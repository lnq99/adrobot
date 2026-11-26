import { useState } from "react";
import CountrySelect from "../components/CountrySelect";
import OfferPicker from "../components/OfferPicker";
import { api } from "../api";

export default function CreateCampaign() {
  const [name, setName] = useState("test_quang_");
  const [geos, setGeos] = useState<string[]>([]);
  const [offerId, setOfferId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  async function submit() {
    try {
      const c = await api.createCampaign(name, geos, offerId!);
      setMsg(`Created campaign #${c.keitaro_campaign_id} (${c.name})`);
    } catch (e) {
      setMsg(`Error: ${(e as Error).message}`);
    }
  }

  return (
    <div>
      <h2>Create campaign</h2>
      <div>
        <label>
          Name <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      <div>
        Countries:
        <CountrySelect value={geos} onChange={setGeos} />
      </div>
      <div>
        Offer: {offerId ?? "none"}
        <OfferPicker onPick={setOfferId} />
      </div>
      <button onClick={submit} disabled={!geos.length || !offerId}>
        Create
      </button>
      <p>{msg}</p>
    </div>
  );
}

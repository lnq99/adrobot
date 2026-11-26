import { useState } from "react";
import CountrySelect from "../components/CountrySelect";
import OfferPicker from "../components/OfferPicker";
import { api } from "../api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle>
          <h2 className="text-xl font-semibold">Create campaign</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700" htmlFor="campaign-name">
            Name
          </label>
          <Input
            id="campaign-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Name"
          />
        </div>

        <div className="space-y-1">
          <div className="text-sm font-medium text-slate-700">Countries</div>
          <CountrySelect value={geos} onChange={setGeos} />
        </div>

        <div className="space-y-1">
          <div className="text-sm font-medium text-slate-700">
            Offer: {offerId ?? "none"}
          </div>
          <OfferPicker onPick={setOfferId} />
        </div>

        <Button
          onClick={submit}
          disabled={!geos.length || !offerId}
          className="w-full"
        >
          Create
        </Button>

        {msg && (
          <p className={`text-sm ${msg.startsWith("Error") ? "text-red-600" : "text-green-700"}`}>
            {msg}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

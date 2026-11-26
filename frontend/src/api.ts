import type { Campaign, Stream } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  listCampaigns: () => req<Campaign[]>("/api/campaigns"),
  createCampaign: (name: string, geos: string[], offer_id: number) =>
    req<Campaign>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify({ name, geos, offer_id }),
    }),
  getStreams: (id: number) => req<Stream[]>(`/api/campaigns/${id}/streams`),
  fetchStreams: (id: number) =>
    req<Stream[]>(`/api/campaigns/${id}/fetch`, { method: "POST" }),
  searchOffers: (q: string) =>
    req<{ id: number; name: string }[]>(`/api/offers?q=${encodeURIComponent(q)}`),
  addOffer: (sid: number, offer_id: number) =>
    req<Stream>(`/api/streams/${sid}/offers`, {
      method: "POST",
      body: JSON.stringify({ offer_id }),
    }),
  removeOffer: (sid: number, oid: number) =>
    req<Stream>(`/api/streams/${sid}/offers/${oid}`, { method: "DELETE" }),
  bringBack: (sid: number, oid: number) =>
    req<Stream>(`/api/streams/${sid}/offers/${oid}/bring-back`, { method: "POST" }),
  pin: (sid: number, oid: number, pinned: boolean, share: number | null) =>
    req<Stream>(`/api/streams/${sid}/offers/${oid}/pin`, {
      method: "POST",
      body: JSON.stringify({ pinned, share }),
    }),
  push: (sid: number) => req<Stream>(`/api/streams/${sid}/push`, { method: "POST" }),
  cancel: (sid: number) => req<Stream>(`/api/streams/${sid}/cancel`, { method: "POST" }),
};

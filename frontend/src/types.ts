export type Offer = {
  keitaro_offer_id: number;
  offer_name: string;
  share: number;
  status: "active" | "removed";
  origin: "local" | "keitaro";
  pinned: boolean;
};

export type Stream = {
  id: number;
  keitaro_stream_id: number;
  position: number;
  kind: "offers" | "opaque";
  is_dirty: boolean;
  offers: Offer[];
};

export type Campaign = {
  id: number;
  keitaro_campaign_id: number;
  name: string;
  alias: string;
  geos: string[];
};

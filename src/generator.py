"""Dataset generator: entities, wallets, UTXO transactions, peers, network events."""
import hashlib
import random
from datetime import datetime, timedelta

import pandas as pd

from src.config import Config


class DatasetGenerator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rng = random.Random(cfg.get("seed", 42))
        self.start = datetime.fromisoformat(cfg.get("dataset.start_date"))
        self.end = datetime.fromisoformat(cfg.get("dataset.end_date"))
        self.block_height = 0

    # ---------- helpers ----------
    def _ts(self):
        span = int((self.end - self.start).total_seconds())
        return (self.start + timedelta(seconds=self.rng.randint(0, span))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def _hash(self, s):
        return hashlib.sha256(str(s).encode()).hexdigest()[:32]

    # ---------- entities ----------
    def _entities(self):
        n = self.cfg.get("dataset.entities", 400)
        ratios = self.cfg.get("scenarios")
        types = ["normal", "peeling", "layering", "risk_propagation"]
        weights = [
            ratios["normal_ratio"],
            ratios["peeling_ratio"],
            ratios["layering_ratio"],
            ratios["risk_propagation_ratio"],
        ]
        gt = {"normal": "low", "peeling": "high",
              "layering": "high", "risk_propagation": "critical"}

        rows = []
        counters = {"peeling": 0, "layering": 0, "risk_propagation": 0}
        for i in range(n):
            etype = self.rng.choices(types, weights=weights)[0]
            if etype == "normal":
                sid = f"N{self.rng.randint(1, 9999):04d}"
            else:
                counters[etype] += 1
                group = (counters[etype] - 1) // 5 + 1
                prefix = {"peeling": "P", "layering": "L",
                          "risk_propagation": "R"}[etype]
                sid = f"{prefix}{group:04d}"
            rows.append({
                "entity_id": f"ENT_{i+1:06d}",
                "entity_type": etype,
                "scenario_id": sid,
                "risk_ground_truth": gt[etype],
                "created_at": self._ts(),
            })
        return pd.DataFrame(rows)

    # ---------- wallets ----------
    def _wallets(self, entities):
        per = self.cfg.get("dataset.wallets_per_entity", 4)
        rows = []
        wid = 0
        for e in entities.itertuples():
            if e.entity_type == "peeling":
                k = self.rng.randint(3, 6)
            elif e.entity_type == "layering":
                k = self.rng.randint(4, 8)
            elif e.entity_type == "risk_propagation":
                k = self.rng.randint(4, 7)
            else:
                k = self.rng.randint(1, per)

            for _ in range(k):
                wid += 1
                wt = "normal"
                if e.entity_type in ("peeling", "layering", "risk_propagation"):
                    wt = "suspicious" if self.rng.random() < 0.8 else "normal"
                rows.append({
                    "wallet_id": f"W_{wid:08d}",
                    "entity_id": e.entity_id,
                    "wallet_type": wt,
                    "created_at": e.created_at,
                })
        return pd.DataFrame(rows)

    # ---------- transactions ----------
    def _transactions(self, wallets, entities):
        n = self.cfg.get("dataset.transactions", 4000)

        wallet_entity = dict(zip(wallets["wallet_id"], wallets["entity_id"]))
        entity_type = dict(zip(entities["entity_id"], entities["entity_type"]))
        entity_scenario = dict(zip(entities["entity_id"], entities["scenario_id"]))

        # scenario -> list of wallets
        scenario_wallets = {}
        for w in wallets.itertuples():
            sid = entity_scenario[w.entity_id]
            scenario_wallets.setdefault(sid, []).append(w.wallet_id)

        # UTXO pool
        utxo = {}
        for w in wallets["wallet_id"]:
            utxo[w] = []
            for _ in range(self.rng.randint(1, 2)):
                amt = round(self.rng.uniform(0.1, 5.0), 8)
                txid = self._hash(f"init-{w}-{self.rng.random()}")
                utxo[w].append({"txid": txid, "idx": 0,
                                "amount": amt, "spent": False})

        txs, ins, outs = [], [], []
        all_wallets = wallets["wallet_id"].tolist()

        for _ in range(n):
            # pick sender
            senders = [w for w in all_wallets
                       if any(not u["spent"] for u in utxo[w])]
            if not senders:
                break
            sender = self.rng.choice(senders)
            avail = [u for u in utxo[sender] if not u["spent"]]
            n_in = min(len(avail), self.rng.randint(1, 2))
            chosen = self.rng.sample(avail, n_in)
            total_in = round(sum(u["amount"] for u in chosen), 8)

            # fee
            fee = round(self.rng.uniform(0.00002, 0.0008), 8)
            if fee >= total_in:
                continue
            output_total = round(total_in - fee, 8)

            # choose pattern based on sender's entity
            etype = entity_type.get(wallet_entity[sender], "normal")
            sid = entity_scenario.get(wallet_entity[sender], None)

            if etype == "peeling" and sid in scenario_wallets:
                receivers = self._peeling_receivers(sender, sid, scenario_wallets)
            elif etype == "layering" and sid in scenario_wallets:
                receivers = self._layering_receivers(sender, sid, scenario_wallets)
            elif etype == "risk_propagation" and sid in scenario_wallets:
                receivers = self._propagation_receivers(sender, sid, scenario_wallets)
            else:
                receivers = [self.rng.choice([w for w in all_wallets if w != sender])]

            # split amount across receivers
            amounts = self._split(output_total, len(receivers))

            # build tx
            self.block_height += 1
            ts = self._ts()
            txid = self._hash(f"{sender}{receivers}{total_in}{ts}{self.block_height}")
            txs.append({
                "txid": txid,
                "timestamp": ts,
                "input_count": n_in,
                "output_count": len(receivers),
                "input_value": total_in,
                "output_value": round(sum(amounts), 8),
                "fee": fee,
                "script_type": self.rng.choice(["P2PKH", "P2SH", "P2WPKH", "P2WSH"]),
                "block_height": self.block_height,
                "confirmed": self.rng.random() < 0.9,
                "sender_entity": wallet_entity[sender],
                "pattern": etype,
            })

            # inputs
            for j, u in enumerate(chosen):
                ins.append({
                    "txid": txid,
                    "input_index": j,
                    "previous_txid": u["txid"],
                    "previous_output_index": u["idx"],
                    "amount": u["amount"],
                })
                u["spent"] = True

            # outputs
            for j, (r, amt) in enumerate(zip(receivers, amounts)):
                outs.append({
                    "txid": txid,
                    "output_index": j,
                    "wallet_id": r,
                    "amount": amt,
                })
                utxo.setdefault(r, []).append({
                    "txid": txid, "idx": j, "amount": amt, "spent": False,
                })

        return pd.DataFrame(txs), pd.DataFrame(ins), pd.DataFrame(outs)

    def _split(self, total, k):
        if k <= 1:
            return [round(total, 8)]
        props = [self.rng.uniform(0.1, 1.0) for _ in range(k)]
        s = sum(props)
        parts = [round(total * p / s, 8) for p in props[:-1]]
        parts.append(round(total - sum(parts), 8))
        return parts

    def _peeling_receivers(self, sender, sid, scenario_wallets):
        pool = [w for w in scenario_wallets[sid] if w != sender]
        if not pool:
            return [sender]
        return [self.rng.choice(pool), sender]  # peel + change

    def _layering_receivers(self, sender, sid, scenario_wallets):
        pool = [w for w in scenario_wallets[sid] if w != sender]
        if not pool:
            return [sender]
        k = min(len(pool), self.rng.randint(3, 6))
        return self.rng.sample(pool, k)

    def _propagation_receivers(self, sender, sid, scenario_wallets):
        pool = [w for w in scenario_wallets[sid] if w != sender]
        if not pool:
            return [sender]
        return [self.rng.choice(pool)]

    # ---------- peers ----------
    def _peers(self):
        n = self.cfg.get("dataset.peers", 100)
        rows = []
        for i in range(n):
            rows.append({
                "peer_id": f"P_{i+1:06d}",
                "ip": self.rng.choice(
                    ["192.0.2.", "198.51.100.", "203.0.113."]
                ) + str(self.rng.randint(1, 254)),
                "port": self.rng.choice([8333, 8333, 8333, 18333, 18444]),
                "country": self.rng.choice(
                    ["US", "DE", "NL", "SG", "IN", "RU", "BR", "JP"]
                ),
            })
        return pd.DataFrame(rows)

    # ---------- network events ----------
    def _network_events(self, txs, peers):
        if txs.empty or peers.empty:
            return pd.DataFrame()

        miss = self.cfg.get("dataset.missing_data_prob", 0.05)
        peer_ids = peers["peer_id"].tolist()
        rows = []
        for t in txs.itertuples():
            if self.rng.random() < miss:
                continue
            k = self.rng.randint(2, 8)
            obs = self.rng.sample(peer_ids, min(k, len(peer_ids)))
            for i, p in enumerate(obs):
                rows.append({
                    "event_id": f"E_{len(rows)+1:08d}",
                    "txid": t.txid,
                    "peer_id": p,
                    "msg_type": self.rng.choice(["INV", "GETDATA", "TX", "BLOCK"]),
                    "hop": i,
                    "timestamp": t.timestamp,
                })
        return pd.DataFrame(rows)

    # ---------- entry point ----------
    def generate(self):
        entities = self._entities()
        wallets = self._wallets(entities)
        txs, ins, outs = self._transactions(wallets, entities)
        peers = self._peers()
        events = self._network_events(txs, peers)
        return {
            "entities": entities,
            "wallets": wallets,
            "transactions": txs,
            "inputs": ins,
            "outputs": outs,
            "peers": peers,
            "network_events": events,
        }
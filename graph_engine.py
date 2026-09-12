"""Build wallet graph and extract features for ML."""
import networkx as nx
import pandas as pd


class GraphEngine:
    def __init__(self, data):
        self.data = data
        self.G = self._build()

    def _build(self):
        G = nx.DiGraph()
        outs = self.data["outputs"]
        ins = self.data["inputs"]
        txs = self.data["transactions"].set_index("txid")

        # add wallet nodes
        for w in self.data["wallets"]["wallet_id"]:
            G.add_node(w)

        # build wallet->wallet edges via UTXO flow
        # map txid -> sender (from inputs -> previous output's wallet)
        # For simplicity, we infer sender wallet from inputs' previous outputs
        out_lookup = {}
        for o in outs.itertuples():
            out_lookup[(o.txid, o.output_index)] = o.wallet_id

        # map previous_txid+index -> wallet (spent from)
        for i in ins.itertuples():
            src = out_lookup.get((i.previous_txid, i.previous_output_index))
            if src is None:
                continue
            for o in outs[outs["txid"] == i.txid].itertuples():
                if src == o.wallet_id:
                    continue
                w = G.get_edge_data(src, o.wallet_id, {}).get("weight", 0)
                G.add_edge(src, o.wallet_id, weight=w + float(o.amount))

        # add simple tx pattern edges from peeling/layering scenario
        for t in txs.reset_index().itertuples():
            if t.pattern in ("peeling", "layering", "risk_propagation"):
                # already covered above; optionally boost weight
                pass

        return G

    def extract_features(self):
        G = self.G
        wallets = self.data["wallets"]
        outs = self.data["outputs"]
        ins = self.data["inputs"]
        txs = self.data["transactions"]

        # base stats
        out_counts = outs.groupby("wallet_id").size().rename("out_count")
        out_amount = outs.groupby("wallet_id")["amount"].sum().rename("out_amount")

        sent_tx = ins.merge(
            outs[["txid", "wallet_id"]].rename(columns={"wallet_id": "src"}),
            left_on="previous_txid", right_on="txid", how="left"
        )
        sent = sent_tx.groupby("src").size().rename("sent_tx_count")

        feat = pd.DataFrame(index=list(G.nodes()))
        feat["degree"] = [G.degree(n) for n in feat.index]
        feat["in_degree"] = [G.in_degree(n) for n in feat.index]
        feat["out_degree"] = [G.out_degree(n) for n in feat.index]
        feat["pagerank"] = pd.Series(nx.pagerank(G, weight="weight"))
        feat["clustering"] = pd.Series(nx.clustering(G.to_undirected()))
        feat["out_count"] = out_counts.reindex(feat.index).fillna(0)
        feat["out_amount"] = out_amount.reindex(feat.index).fillna(0)
        feat["sent_tx_count"] = sent.reindex(feat.index).fillna(0)

        # join entity type + wallet type
        wmap = wallets.set_index("wallet_id")
        feat["wallet_type"] = wmap["wallet_type"].reindex(feat.index)
        ent = self.data["entities"].set_index("entity_id")
        feat["entity_id"] = wmap["entity_id"].reindex(feat.index)
        feat["entity_type"] = ent["entity_type"].reindex(feat["entity_id"]).values
        feat["ground_truth_risk"] = ent["risk_ground_truth"].reindex(
            feat["entity_id"]
        ).values
        feat["scenario_id"] = ent["scenario_id"].reindex(feat["entity_id"]).values

        # fan-out (unique receivers)
        out_edges = pd.DataFrame(
            [(u, v) for u, v in G.edges()], columns=["src", "dst"]
        )
        fanout = out_edges.groupby("src")["dst"].nunique().rename("fanout")
        feat["fanout"] = fanout.reindex(feat.index).fillna(0)

        return feat.reset_index().rename(columns={"index": "wallet_id"})
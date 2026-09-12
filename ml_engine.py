"""ML engine: Isolation Forest + RandomForest + rule engine + combined risk score."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder


class MLEngine:
    def __init__(self, cfg):
        self.cfg = cfg

    # ---------- helpers ----------
    def _rule_scores(self, feat):
        """Rule-based component."""
        scores = np.zeros(len(feat))

        # peeling: high fanout + suspicious wallet + high out_count
        peel = (
            (feat["fanout"] >= 2)
            & (feat["out_count"] >= 5)
            & (feat["wallet_type"] == "suspicious")
        )
        scores += peel.astype(float) * 40

        # layering: very high fanout
        layer = feat["fanout"] >= 4
        scores += layer.astype(float) * 35

        # propagation: high in-degree with suspicious source
        prop = (feat["in_degree"] >= 3) & (feat["entity_type"] == "risk_propagation")
        scores += prop.astype(float) * 40

        # large amounts
        q = feat["out_amount"].quantile(0.95)
        big = feat["out_amount"] >= q
        scores += big.astype(float) * 20

        return np.clip(scores, 0, 100)

    def _risk_bucket(self, score):
        c = self.cfg.get("risk_thresholds.critical", 90)
        h = self.cfg.get("risk_thresholds.high", 70)
        m = self.cfg.get("risk_thresholds.medium", 40)
        if score >= c:
            return "critical"
        if score >= h:
            return "high"
        if score >= m:
            return "medium"
        return "low"

    # ---------- main ----------
    def run(self, feat):
        df = feat.copy()

        # encode categorical for classifier
        feature_cols = [
            "degree", "in_degree", "out_degree", "pagerank", "clustering",
            "out_count", "out_amount", "sent_tx_count", "fanout",
        ]
        X = df[feature_cols].fillna(0).astype(float).values

        # anomaly
        iso = IsolationForest(contamination=0.1, random_state=42)
        iso.fit(X)
        anomaly_raw = -iso.score_samples(X)
        anomaly_norm = (anomaly_raw - anomaly_raw.min()) / (
            anomaly_raw.max() - anomaly_raw.min() + 1e-9
        )
        df["anomaly_score"] = anomaly_norm * 100

        # classifier (trained on ground truth risk → 4 classes)
        le = LabelEncoder()
        y = le.fit_transform(df["ground_truth_risk"])
        clf = RandomForestClassifier(n_estimators=200, random_state=42)
        clf.fit(X, y)
        proba = clf.predict_proba(X)
        # weight: higher classes are riskier
        class_weights = {c: i for i, c in enumerate(le.classes_)}
        weights = np.array([class_weights[c] for c in le.classes_], dtype=float)
        if weights.max() > 0:
            weights = weights / weights.max()
        cls_score = (proba * weights).sum(axis=1) * 100
        df["classifier_score"] = cls_score

        # rules
        df["rule_score"] = self._rule_scores(df)

        # correlation: suspicious wallet_type + suspicious scenario
        df["correlation_score"] = (
            (df["wallet_type"] == "suspicious").astype(float) * 50
            + (df["entity_type"] != "normal").astype(float) * 50
        )

        # weighted total
        aw = self.cfg.get("risk.anomaly_weight", 0.25)
        cw = self.cfg.get("risk.classifier_weight", 0.35)
        rw = self.cfg.get("risk.rule_weight", 0.25)
        ww = self.cfg.get("risk.correlation_weight", 0.15)
        df["risk_score"] = (
            df["anomaly_score"] * aw
            + df["classifier_score"] * cw
            + df["rule_score"] * rw
            + df["correlation_score"] * ww
        ).round(2)

        df["risk_level"] = df["risk_score"].apply(self._risk_bucket)
        return df
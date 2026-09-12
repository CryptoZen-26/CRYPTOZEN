"""Page renderers matching CRYPTOZEN layout."""
import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


RISK_BADGE = {
    "critical": '<span class="cz-bg-critical">CRITICAL</span>',
    "high": '<span class="cz-bg-high">HIGH</span>',
    "medium": '<span class="cz-bg-medium">MEDIUM</span>',
    "low": '<span class="cz-bg-low">LOW</span>',
}


def _metric_card(value, label, color="#60a5fa"):
    return f"""
    <div class="cz-card">
        <p class="cz-value" style="color:{color};">{value}</p>
        <p class="cz-label">{label}</p>
    </div>
    """


# ---------- Dashboard ----------
def dashboard(data, feat, graph_engine):
    st.markdown("## Investigation Dashboard")
    st.caption("AI-Powered Bitcoin Transaction Monitoring & Forensic Investigation")

    n_tx = len(data["transactions"])
    n_wallet = len(data["wallets"])
    alerts = feat[feat["risk_level"].isin(["critical", "high"])]
    n_alerts = len(alerts)
    n_critical = (feat["risk_level"] == "critical").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_metric_card(f"{n_tx:,}", "Total Transactions", "#60a5fa"),
                unsafe_allow_html=True)
    c2.markdown(_metric_card(f"{n_wallet:,}", "Unique Wallets", "#f59e0b"),
                unsafe_allow_html=True)
    c3.markdown(_metric_card(f"{n_alerts:,}", "Active Alerts", "#fb923c"),
                unsafe_allow_html=True)
    c4.markdown(_metric_card(f"{n_critical:,}", "Critical Threats", "#ef4444"),
                unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])

    with left:
        st.markdown("### Alert Queue")
        top = alerts.sort_values("risk_score", ascending=False).head(10)
        if top.empty:
            st.info("No alerts. Dataset clean.")
        for row in top.itertuples():
            st.markdown(
                f"""
                <div class="cz-alert">
                    <div>
                        <span style="font-family: monospace; color:#f59e0b;">
                            {row.wallet_id}
                        </span>
                        &nbsp; {RISK_BADGE.get(row.risk_level, '')}
                        &nbsp; <span style="color:#9ca3af;font-size:12px;">
                        {row.entity_type}</span>
                    </div>
                    <div style="color:#6b7280;font-size:12px;">
                        score {row.risk_score:.1f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        st.markdown("### Forensic Evidence Locker")
        total = max(len(feat), 1)
        for lvl, label in [("critical", "Critical"), ("high", "High"),
                           ("medium", "Medium"), ("low", "Low")]:
            pct = (feat["risk_level"] == lvl).sum() / total * 100
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            padding:6px 0;">
                    <span class="cz-{lvl}">{label}</span>
                    <span style="color:#6b7280;">{pct:.1f}%</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------- Transaction Graph ----------
def transactions(data, feat, graph_engine):
    st.markdown("## Transaction Graph")
    st.caption("Real transaction flow analysis")

    G = graph_engine.G
    if G.number_of_nodes() == 0:
        st.info("No graph data.")
        return

    # limit for render
    sub_nodes = list(G.nodes())[:150]
    H = G.subgraph(sub_nodes)
    pos = nx.spring_layout(H, seed=42, k=0.5)

    risk_map = dict(zip(feat["wallet_id"], feat["risk_level"]))
    color_map = {"critical": "#ef4444", "high": "#f97316",
                 "medium": "#eab308", "low": "#22c55e"}

    edge_x, edge_y = [], []
    for u, v in H.edges():
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=0.5, color="#374151"), hoverinfo="none",
    )

    node_x = [pos[n][0] for n in H.nodes()]
    node_y = [pos[n][1] for n in H.nodes()]
    node_c = [color_map.get(risk_map.get(n, "low"), "#22c55e") for n in H.nodes()]
    node_text = [f"{n}<br>risk: {risk_map.get(n, 'low')}" for n in H.nodes()]

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers",
        marker=dict(size=10, color=node_c, line=dict(color="#0a0a0f", width=1)),
        text=node_text, hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False, height=600,
        plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
        font=dict(color="#e5e7eb"),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Top risky wallets")
    top = feat.sort_values("risk_score", ascending=False).head(20)
    st.dataframe(
        top[["wallet_id", "entity_type", "fanout", "risk_score", "risk_level"]],
        use_container_width=True, hide_index=True,
    )


# ---------- Propagation Timeline ----------
def timeline(data, feat, graph_engine):
    st.markdown("## Propagation Timeline")
    st.caption("Transaction propagation and alert timeline")

    txs = data["transactions"].copy()
    txs = txs.sort_values("timestamp").tail(30)

    for row in txs.itertuples():
        lvl = "low"
        if row.pattern == "peeling":
            lvl = "critical"
        elif row.pattern == "layering":
            lvl = "high"
        elif row.pattern == "risk_propagation":
            lvl = "critical"

        badge = RISK_BADGE[lvl]
        st.markdown(
            f"""
            <div style="border-left:2px solid #1f2937; padding-left:14px;
                        margin-bottom:12px; position:relative;">
                <div style="display:flex;justify-content:space-between;">
                    <div>
                        <span style="font-family:monospace;color:#f59e0b;">
                            {row.txid[:20]}…</span>
                        &nbsp; {badge}
                        &nbsp; <span style="color:#9ca3af;font-size:12px;">
                            {row.pattern}</span>
                    </div>
                    <span style="color:#6b7280;font-size:11px;">
                        {row.timestamp}</span>
                </div>
                <div style="color:#6b7280;font-size:12px;margin-top:4px;">
                    {row.input_count} in / {row.output_count} out |
                    {row.input_value:.4f} BTC | fee {row.fee:.6f}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------- Alerts ----------
def alerts(data, feat, graph_engine):
    st.markdown("## Alert Queue")
    st.caption("Real-time alert monitoring and management")

    al = feat[feat["risk_level"].isin(["critical", "high"])].sort_values(
        "risk_score", ascending=False
    )
    if al.empty:
        st.info("No alerts.")
        return

    for row in al.head(50).itertuples():
        st.markdown(
            f"""
            <div class="cz-alert">
                <div>
                    <span style="font-family:monospace;color:#f59e0b;">
                        {row.wallet_id}</span>
                    &nbsp; {RISK_BADGE[row.risk_level]}
                    &nbsp; <span style="color:#9ca3af;font-size:12px;">
                        {row.entity_type}</span>
                </div>
                <div style="color:#6b7280;font-size:12px;">
                    score {row.risk_score:.1f} | fanout {row.fanout:.0f}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------- Geographic ----------
def geographic(data, feat, graph_engine):
    st.markdown("## Geographic Analysis")
    st.caption("Geographic transaction mapping and ASN correlation")

    peers = data["peers"]
    if peers.empty:
        st.info("No peers.")
        return

    counts = peers["country"].value_counts()
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color="#f59e0b",
    ))
    fig.update_layout(
        plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
        font=dict(color="#e5e7eb"), height=400,
        xaxis=dict(gridcolor="#1f2937"),
        yaxis=dict(gridcolor="#1f2937"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Peer list")
    st.dataframe(peers.head(50), use_container_width=True, hide_index=True)


# ---------- Reports ----------
def reports(data, feat, graph_engine):
    st.markdown("## Forensic Reports")
    st.caption("Generate and export forensic investigation reports")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Generate Report")
        if st.button("Export Risk Scores CSV"):
            csv = feat.to_csv(index=False).encode()
            st.download_button("Download CSV", csv,
                               file_name="risk_scores.csv", mime="text/csv")

        if st.button("Export Alerts CSV"):
            al = feat[feat["risk_level"].isin(["critical", "high"])]
            csv = al.to_csv(index=False).encode()
            st.download_button("Download Alerts", csv,
                               file_name="alerts.csv", mime="text/csv")

        if st.button("Export Full Transactions CSV"):
            csv = data["transactions"].to_csv(index=False).encode()
            st.download_button("Download Transactions", csv,
                               file_name="transactions.csv", mime="text/csv")

    with c2:
        st.markdown("### Summary")
        st.markdown(f"""
        - Total wallets: **{len(feat)}**
        - Critical: **{(feat['risk_level']=='critical').sum()}**
        - High: **{(feat['risk_level']=='high').sum()}**
        - Medium: **{(feat['risk_level']=='medium').sum()}**
        - Low: **{(feat['risk_level']=='low').sum()}**
        """)


PAGES = {
    "dashboard": ("Dashboard Overview", dashboard),
    "transactions": ("Transaction Graph", transactions),
    "timeline": ("Propagation Timeline", timeline),
    "alerts": ("Alert Queue", alerts),
    "geographic": ("Geographic Analysis", geographic),
    "reports": ("Forensic Reports", reports),
}
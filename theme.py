"""Inject CRYPTOZEN dark theme into Streamlit."""
import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        .stApp {
            background: #0a0a0f;
            color: #e5e7eb;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', Roboto, sans-serif;
        }
        header[data-testid="stHeader"] { background: transparent; }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #0f0f1a;
            border-right: 1px solid #1f2937;
        }
        [data-testid="stSidebar"] * { color: #9ca3af; }

        /* Sidebar nav buttons */
        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            background: transparent;
            border: none;
            color: #6b7280;
            text-align: left;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(245, 158, 11, 0.1);
            color: #f59e0b;
        }
        [data-testid="stSidebar"] .stButton > button:focus {
            box-shadow: none;
        }

        /* Headings */
        h1, h2, h3, h4 { color: #ffffff !important; }
        p, span, label { color: #e5e7eb; }

        /* Metric cards */
        .cz-card {
            background: #0f0f1a;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        .cz-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(245, 158, 11, 0.15);
        }
        .cz-label {
            color: #9ca3af;
            font-size: 13px;
            margin-top: 4px;
        }
        .cz-value {
            font-size: 28px;
            font-weight: 700;
        }

        /* Risk colors */
        .cz-critical { color: #ef4444; }
        .cz-high { color: #f97316; }
        .cz-medium { color: #eab308; }
        .cz-low { color: #22c55e; }
        .cz-bg-critical { background: rgba(239,68,68,0.15); color:#ef4444;
                          padding:2px 10px; border-radius:4px; font-size:11px;}
        .cz-bg-high { background: rgba(249,115,22,0.15); color:#f97316;
                      padding:2px 10px; border-radius:4px; font-size:11px;}
        .cz-bg-medium { background: rgba(234,179,8,0.15); color:#eab308;
                        padding:2px 10px; border-radius:4px; font-size:11px;}
        .cz-bg-low { background: rgba(34,197,94,0.15); color:#22c55e;
                     padding:2px 10px; border-radius:4px; font-size:11px;}

        /* Alert row */
        .cz-alert {
            display: flex; justify-content: space-between;
            align-items: center;
            padding: 12px; background: #1a1a2e;
            border-radius: 8px; border: 1px solid #1f2937;
            margin-bottom: 8px;
        }

        /* Logo */
        .cz-logo {
            display: flex; align-items: center; gap: 14px;
            padding: 8px 12px; margin-bottom: 24px;
            border-radius: 12px;
            background: linear-gradient(135deg,
                rgba(245,158,11,0.05), rgba(245,158,11,0.01));
            border: 1px solid rgba(245,158,11,0.08);
        }
        .cz-logo-icon {
            width: 48px; height: 48px;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            border-radius: 12px; display: flex; align-items: center;
            justify-content: center; font-weight: 900; color: #fff;
            font-size: 20px;
            box-shadow: 0 0 40px rgba(245,158,11,0.15);
        }
        .cz-logo-main { font-size: 22px; font-weight: 800; color: #fff; }
        .cz-logo-main .hl { color: #f59e0b; }
        .cz-logo-tag { font-size: 9px; color: #6b7280;
                       letter-spacing: 3px; text-transform: uppercase; }

        /* Tables */
        .stDataFrame { background: #0f0f1a; border-radius: 8px; }

        /* Buttons outside sidebar */
        .stButton > button {
            background: rgba(245,158,11,0.15);
            color: #f59e0b;
            border: 1px solid rgba(245,158,11,0.2);
            border-radius: 8px;
            font-weight: 500;
        }
        .stButton > button:hover {
            background: rgba(245,158,11,0.25);
            color: #fbbf24;
        }

        .block-container { padding-top: 1.5rem; max-width: 1400px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def logo_html():
    return """
    <div class="cz-logo">
        <div class="cz-logo-icon">CZ</div>
        <div>
            <div class="cz-logo-main">CRYPTO<span class="hl">ZEN</span></div>
            <div class="cz-logo-tag">TRADE • SECURE • EVOLVE</div>
        </div>
    </div>
    """
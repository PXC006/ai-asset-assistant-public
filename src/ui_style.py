import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


def apply_global_style() -> None:
    """Apply the dark financial terminal style used across the app."""
    pio.templates["private_wealth"] = go.layout.Template(
        layout={
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(7,13,18,0.72)",
            "font": {
                "color": "#CBD5E1",
                "family": 'Inter, "Microsoft YaHei UI", "Microsoft YaHei", sans-serif',
            },
            "title": {"font": {"color": "#F8FAFC"}},
            "xaxis": {
                "gridcolor": "rgba(214,178,110,0.08)",
                "linecolor": "rgba(214,178,110,0.12)",
                "zerolinecolor": "rgba(214,178,110,0.10)",
                "tickfont": {"color": "#94A3B8"},
                "title": {"font": {"color": "#CBD5E1"}},
            },
            "yaxis": {
                "gridcolor": "rgba(214,178,110,0.08)",
                "linecolor": "rgba(214,178,110,0.12)",
                "zerolinecolor": "rgba(214,178,110,0.10)",
                "tickfont": {"color": "#94A3B8"},
                "title": {"font": {"color": "#CBD5E1"}},
            },
            "legend": {
                "font": {"color": "#CBD5E1"},
                "bgcolor": "rgba(8,15,18,0.42)",
                "bordercolor": "rgba(214,178,110,0.12)",
                "borderwidth": 1,
            },
            "hoverlabel": {
                "bgcolor": "rgba(8,15,18,0.94)",
                "bordercolor": "rgba(214,178,110,0.34)",
                "font": {"color": "#F8FAFC"},
            },
            "colorway": [
                "#D6B26E",
                "#5B8DEF",
                "#C89B3C",
                "#10B981",
                "#8EA4C8",
                "#B88A3A",
                "#D1A85A",
                "#A55D5D",
            ],
            "piecolorway": [
                "#D6B26E",
                "#5B8DEF",
                "#C89B3C",
                "#8EA4C8",
                "#10B981",
                "#B88A3A",
            ],
        }
    )
    pio.templates.default = "private_wealth"
    st.markdown(
        """
        <style>
        :root {
            --bg-main: #060A0D;
            --bg-sidebar: #05080A;
            --bg-panel: rgba(7, 12, 15, 0.94);
            --bg-card: rgba(7, 13, 18, 0.84);
            --bg-input: rgba(9, 15, 20, 0.92);
            --text-main: #F8FAFC;
            --text-sub: #CBD5E1;
            --text-muted: #94A3B8;
            --border: rgba(214,178,110,0.12);
            --border-strong: rgba(214,178,110,0.32);
            --gold: #D6B26E;
            --gold-deep: #A97824;
            --blue: #102235;
            --blue-bright: #5B8DEF;
            --green: #10B981;
            --red: #EF4444;
            --orange: #F59E0B;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:
                radial-gradient(circle at 84% 18%, rgba(214,178,110,0.12), transparent 31%),
                radial-gradient(circle at 70% 42%, rgba(200,155,60,0.045), transparent 34%),
                radial-gradient(circle at 18% 16%, rgba(16,34,53,0.24), transparent 32%),
                radial-gradient(circle at 6% 74%, rgba(11,23,32,0.26), transparent 36%),
                radial-gradient(circle at 52% 104%, rgba(214,178,110,0.062), transparent 32%),
                linear-gradient(145deg, #05080A 0%, #071014 42%, #0B1116 72%, #0B1720 100%) !important;
            color: var(--text-main) !important;
            font-family: Inter, "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
        }

        [data-testid="stAppViewContainer"] {
            position: relative;
            overflow: hidden;
        }

        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background-image:
                url("data:image/svg+xml,%3Csvg width='900' height='720' viewBox='0 0 900 720' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%23D6B26E' stroke-opacity='0.040' stroke-width='1.2'%3E%3Cpath d='M90 -20 C115 96 88 170 132 278 C160 346 130 436 164 548'/%3E%3Cpath d='M124 94 C86 132 54 158 16 174'/%3E%3Cpath d='M132 184 C182 158 218 128 250 82'/%3E%3Cpath d='M146 310 C96 336 62 378 34 430'/%3E%3Cpath d='M154 388 C206 370 254 336 292 292'/%3E%3Cpath d='M760 600 C798 508 796 436 836 346 C864 284 842 202 878 112'/%3E%3Cpath d='M814 432 C774 402 742 366 704 318'/%3E%3Cpath d='M830 282 C870 250 892 224 914 188'/%3E%3C/g%3E%3Cg fill='%23D6B26E' fill-opacity='0.020'%3E%3Cellipse cx='58' cy='142' rx='58' ry='22' transform='rotate(-28 58 142)'/%3E%3Cellipse cx='224' cy='102' rx='72' ry='26' transform='rotate(-36 224 102)'/%3E%3Cellipse cx='54' cy='420' rx='66' ry='24' transform='rotate(-42 54 420)'/%3E%3Cellipse cx='714' cy='322' rx='74' ry='24' transform='rotate(42 714 322)'/%3E%3Cellipse cx='896' cy='188' rx='70' ry='22' transform='rotate(-35 896 188)'/%3E%3C/g%3E%3C/svg%3E"),
                linear-gradient(rgba(214,178,110,0.010) 1px, transparent 1px),
                linear-gradient(90deg, rgba(91,141,239,0.010) 1px, transparent 1px);
            background-size: 900px 720px, 72px 72px, 72px 72px;
            background-position: left top, center, center;
            background-repeat: no-repeat, repeat, repeat;
            opacity: 0.52;
            mask-image: linear-gradient(to bottom, rgba(0,0,0,0.82), rgba(0,0,0,0.24));
            -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,0.82), rgba(0,0,0,0.24));
        }

        [data-testid="stAppViewContainer"]::after {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            opacity: 0.40;
            background-image:
                url("data:image/svg+xml,%3Csvg width='1200' height='720' viewBox='0 0 1200 720' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M700 215 L780 196 L860 210 L940 154 L1018 172 L1170 112' fill='none' stroke='%23D6B26E' stroke-width='2' stroke-opacity='0.030'/%3E%3Cpath d='M710 286 L800 270 L884 276 L960 242 L1040 256 L1180 212' fill='none' stroke='%235B8DEF' stroke-width='2' stroke-opacity='0.026'/%3E%3Cpath d='M790 128 L802 156 M842 118 L842 162 M884 138 L884 180 M930 104 L930 150 M974 126 L974 170' stroke='%23D6B26E' stroke-width='1.4' stroke-opacity='0.028'/%3E%3Cg fill='none' stroke='%23D6B26E' stroke-opacity='0.030'%3E%3Cpath d='M0 635 C150 610 245 660 392 628 C540 596 690 640 842 608 C992 576 1090 620 1200 590'/%3E%3Cpath d='M0 670 C172 648 246 690 410 662 C562 636 702 674 862 650 C1006 628 1110 660 1200 640'/%3E%3Cpath d='M0 704 C160 686 302 712 456 690 C610 668 740 696 900 678 C1040 662 1134 690 1200 676'/%3E%3C/g%3E%3C/svg%3E"),
                radial-gradient(ellipse at 80% 18%, rgba(214,178,110,0.10), transparent 36%),
                linear-gradient(to top, rgba(214,178,110,0.050) 0%, rgba(16,34,53,0.042) 13%, transparent 29%),
                linear-gradient(300deg, transparent 0%, rgba(16,34,53,0.060) 36%, transparent 68%);
            background-repeat: no-repeat, no-repeat, no-repeat, no-repeat;
            background-position: right top, right top, bottom center, center;
            background-size: 74vw auto, 58vw 44vh, 100% 36%, cover;
        }

        [data-testid="stHeader"] {
            background: transparent !important;
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 96% !important;
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-bottom: 3rem !important;
        }

        [data-testid="stSidebar"] {
            position: relative;
            z-index: 2;
            background:
                radial-gradient(circle at 18% 4%, rgba(214,178,110,0.055), transparent 24%),
                radial-gradient(circle at 85% 64%, rgba(16,34,53,0.22), transparent 36%),
                linear-gradient(180deg, #05080A 0%, #071014 45%, #0B1116 100%) !important;
            border-right: 1px solid rgba(214,178,110,0.12);
            box-shadow: 12px 0 34px rgba(0,0,0,0.26), inset -1px 0 0 rgba(255,255,255,0.015);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }
        [data-testid="stSidebar"] * {
            color: var(--text-muted) !important;
        }
        [data-testid="stSidebar"] a,
        [data-testid="stSidebarNav"] a {
            border-radius: 8px;
            padding: 0.48rem 0.65rem;
            margin: 0.12rem 0;
            border-left: 3px solid transparent;
            transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
        }
        [data-testid="stSidebar"] a:hover,
        [data-testid="stSidebarNav"] a:hover {
            background: rgba(214,178,110,0.08) !important;
            border-left-color: rgba(214,178,110,0.34);
            color: var(--text-main) !important;
        }
        [data-testid="stSidebar"] a:hover *,
        [data-testid="stSidebarNav"] a:hover * {
            color: var(--text-main) !important;
        }
        [data-testid="stSidebar"] a[aria-current="page"],
        [data-testid="stSidebarNav"] a[aria-current="page"],
        [data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {
            background: linear-gradient(90deg, rgba(214,178,110,0.18), rgba(214,178,110,0.06)) !important;
            border-left-color: #D6B26E !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 8px 22px rgba(0,0,0,0.18);
        }
        [data-testid="stSidebar"] a[aria-current="page"] *,
        [data-testid="stSidebarNav"] a[aria-current="page"] * {
            color: #F8FAFC !important;
            font-weight: 700 !important;
        }

        h1 {
            color: var(--text-main) !important;
            font-weight: 800 !important;
            letter-spacing: 0 !important;
            margin-bottom: 0.35rem !important;
            padding: 0.78rem 1rem 0.82rem 1.08rem;
            border-left: 2px solid rgba(214,178,110,0.76);
            border-radius: 12px;
            background:
                radial-gradient(circle at 9% 20%, rgba(214,178,110,0.060), transparent 34%),
                linear-gradient(90deg, rgba(7,13,18,0.86), rgba(11,23,32,0.36), rgba(8,16,20,0.025)),
                url("data:image/svg+xml,%3Csvg width='420' height='120' viewBox='0 0 420 120' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 82 L42 74 L84 78 L126 56 L168 62 L210 36 L252 46 L294 28 L336 34 L420 18' fill='none' stroke='%23D6B26E' stroke-width='1.1' stroke-opacity='0.050'/%3E%3Cpath d='M0 102 L56 94 L112 98 L168 82 L224 86 L280 64 L336 70 L420 48' fill='none' stroke='%235B8DEF' stroke-width='1.0' stroke-opacity='0.040'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right center;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 10px 26px rgba(0,0,0,0.14);
        }
        h1:after {
            content: "";
            display: block;
            width: 56px;
            height: 2px;
            margin-top: 0.65rem;
            background: linear-gradient(90deg, rgba(214,178,110,0.70), rgba(214,178,110,0));
            border-radius: 999px;
        }
        h2, h3 {
            color: var(--text-main) !important;
            letter-spacing: 0 !important;
        }
        p, label, span, div {
            color: inherit;
        }
        [data-testid="stCaptionContainer"] {
            color: var(--text-muted) !important;
        }

        div[data-testid="stMetric"],
        .stMetric {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(214,178,110,0.13);
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow:
                0 18px 45px rgba(0,0,0,0.42),
                inset 0 1px 0 rgba(255,255,255,0.035);
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }
        div[data-testid="stMetric"]:hover,
        .stMetric:hover {
            border-color: rgba(214,178,110,0.24);
            box-shadow:
                0 20px 48px rgba(0,0,0,0.45),
                inset 0 1px 0 rgba(255,255,255,0.04);
        }
        div[data-testid="stMetricLabel"] p {
            color: var(--text-muted) !important;
            font-size: 0.82rem !important;
        }
        div[data-testid="stMetricValue"] {
            color: var(--text-main) !important;
            font-weight: 800 !important;
        }

        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        .ui-section-card {
            background: var(--bg-card) !important;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(214,178,110,0.13) !important;
            border-radius: 18px !important;
            padding: 1rem !important;
            box-shadow:
                0 18px 45px rgba(0,0,0,0.42),
                inset 0 1px 0 rgba(255,255,255,0.035);
            transition: border-color 160ms ease, box-shadow 160ms ease;
        }
        div[data-testid="stForm"]:hover,
        div[data-testid="stExpander"]:hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:hover,
        .ui-section-card:hover {
            border-color: rgba(214,178,110,0.24) !important;
        }

        input, textarea, select,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stTextArea"] textarea,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] > div,
        [data-baseweb="base-input"],
        [data-baseweb="select"] {
            background: var(--bg-input) !important;
            color: var(--text-main) !important;
            border: 1px solid rgba(214,178,110,0.12) !important;
            border-radius: 10px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        }
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {
            background: rgba(7,13,18,0.98) !important;
            border: 1px solid rgba(214,178,110,0.16) !important;
            color: var(--text-main) !important;
            box-shadow: 0 18px 45px rgba(0,0,0,0.42);
        }
        [role="option"]:hover,
        [role="option"][aria-selected="true"] {
            background: rgba(214,178,110,0.10) !important;
            color: var(--text-main) !important;
        }
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"] textarea:focus,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        div[data-testid="stDateInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {
            background: rgba(11, 18, 24, 0.96) !important;
            border-color: rgba(214,178,110,0.45) !important;
            box-shadow: 0 0 0 1px rgba(214,178,110,0.12) !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] button,
        button[data-testid="baseButton-primary"],
        button[data-testid="stBaseButton-primary"],
        button[kind="primary"],
        button[data-baseweb="button"] {
            background: linear-gradient(135deg, #A97824 0%, #D6B26E 100%) !important;
            background-color: #A97824 !important;
            color: #0B0F14 !important;
            border: 1px solid rgba(214,178,110,0.45) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            min-height: 2.6rem;
            box-shadow: 0 12px 26px rgba(169,120,36,0.18), inset 0 1px 0 rgba(255,255,255,0.20) !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        div[data-testid="stFormSubmitButton"] button:hover,
        button[data-testid="baseButton-primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover,
        button[kind="primary"]:hover,
        button[data-baseweb="button"]:hover {
            background: linear-gradient(135deg, #C89B3C 0%, #E5C47A 100%) !important;
            background-color: #C89B3C !important;
            border-color: rgba(229,196,122,0.72) !important;
            color: #070B10 !important;
            filter: none;
            box-shadow: 0 0 18px rgba(214,178,110,0.20), 0 12px 28px rgba(0,0,0,0.24) !important;
        }
        [data-testid="stAlert"] {
            background: rgba(12, 28, 44, 0.62) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(96,165,250,0.22) !important;
            border-radius: 12px !important;
            color: var(--text-sub) !important;
            box-shadow: 0 12px 30px rgba(0,0,0,0.22);
        }
        [data-testid="stAlert"] * {
            color: inherit !important;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid rgba(214,178,110,0.10);
            border-radius: 12px;
            overflow: hidden;
            background: var(--bg-panel);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 12px 32px rgba(0,0,0,0.24);
        }
        [data-testid="stDataFrame"] * {
            color: var(--text-sub);
        }
        [data-testid="stTable"] {
            background: var(--bg-panel);
            border: 1px solid rgba(214,178,110,0.10);
            border-radius: 12px;
            overflow: hidden;
        }
        [data-testid="stTable"] thead tr th {
            background: rgba(214,178,110,0.08) !important;
            color: #E5E7EB !important;
            border-color: rgba(214,178,110,0.08) !important;
        }
        [data-testid="stTable"] tbody tr td {
            background: rgba(7,12,15,0.94) !important;
            border-color: rgba(214,178,110,0.08) !important;
        }
        [data-testid="stTable"] tbody tr:hover td {
            background: rgba(214,178,110,0.045) !important;
        }

        .js-plotly-plot, .plot-container {
            background: transparent !important;
        }

        .ui-metric-card {
            background: var(--bg-card);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1px solid rgba(214,178,110,0.14);
            border-radius: 18px;
            padding: 18px 20px;
            min-height: 112px;
            box-shadow:
                0 18px 45px rgba(0,0,0,0.42),
                inset 0 1px 0 rgba(255,255,255,0.035);
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }
        .ui-metric-card:hover {
            border-color: rgba(214,178,110,0.28);
            box-shadow:
                0 20px 48px rgba(0,0,0,0.45),
                inset 0 1px 0 rgba(255,255,255,0.04);
        }
        .ui-metric-title {
            color: var(--text-muted);
            font-size: 0.82rem;
            margin-bottom: 0.55rem;
        }
        .ui-metric-value {
            font-size: 1.65rem;
            line-height: 1.15;
            font-weight: 800;
        }
        .ui-metric-subtitle {
            color: var(--text-muted);
            font-size: 0.82rem;
            margin-top: 0.55rem;
        }
        .ui-value-positive { color: #10B981; }
        .ui-value-negative { color: var(--red); }
        .ui-value-warning { color: var(--orange); }
        .ui-value-neutral { color: var(--text-main); }

        .ui-info-box {
            border-radius: 12px;
            padding: 14px 16px;
            margin: 0.5rem 0;
            border: 1px solid rgba(212,175,55,0.12);
            background: rgba(8,15,18,0.80);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            color: var(--text-sub);
        }
        .ui-info { color: #CBD5E1; border-color: rgba(96,165,250,0.22); background: rgba(12,28,44,0.62); }
        .ui-success { color: #D1FAE5; border-color: rgba(16,185,129,0.24); background: rgba(10,42,32,0.62); }
        .ui-warning { color: #FDE68A; border-color: rgba(214,178,110,0.26); background: rgba(65,48,18,0.58); }
        .ui-danger { color: #FECACA; border-color: rgba(239,68,68,0.24); background: rgba(65,20,20,0.58); }

        .ui-badge {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: rgba(148,163,184,0.10);
            color: var(--text-sub);
            font-size: 0.78rem;
            font-weight: 700;
        }
        .ui-badge-green { color: #8EE6C0; border-color: rgba(16,185,129,0.34); background: rgba(10,42,32,0.44); }
        .ui-badge-blue { color: #A9C5F8; border-color: rgba(91,141,239,0.38); background: rgba(12,28,44,0.52); }
        .ui-badge-orange { color: #F2D68A; border-color: rgba(214,178,110,0.38); background: rgba(65,48,18,0.46); }
        .ui-badge-red { color: #F4B4B4; border-color: rgba(239,68,68,0.32); background: rgba(65,20,20,0.42); }
        .ui-badge-gold { color: var(--gold); border-color: rgba(214,178,110,0.46); background: rgba(214,178,110,0.09); }
        </style>
        """,
        unsafe_allow_html=True,
    )

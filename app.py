# app.py
import io
import time
import math
import random
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="Aurora BioLab — AI Drug Discovery",
    page_icon=None,
    layout="wide"
)

PRIMARY = "#0F172A"
A_TEAL  = "#27B3B1"
A_VIO   = "#6B5DD3"
ROW1_BG = "#ECFDF5"
ROW2_BG = "#EFF6FF"
ROW3_BG = "#ECFEFF"

st.markdown(f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
html, body, [class*="css"] {{
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "SF Pro Text", Inter, Roboto, Arial, sans-serif;
  color: {PRIMARY};
}}
h1,h2,h3{{ font-weight:650; letter-spacing:-0.02em; }}
.section-title {{ font-size:20px; font-weight:600; margin: 0 0 8px 0; }}
.muted {{ color:#667085; font-size:14px; margin-top:4px; }}
.divider {{ height:1px; background:#E5E7EB; margin:16px 0 24px 0; }}
.badges span {{
  display:inline-block; font-size:12px; background:#F3F4F6; color:#111827;
  border:1px solid #E5E7EB; border-radius:8px; padding:4px 8px; margin-right:8px;
}}
.primary-btn button {{
  width: 100%;
  background: linear-gradient(90deg, {A_TEAL} 0%, {A_VIO} 100%) !important;
  color:#fff !important; border:0 !important; border-radius:10px !important;
  padding:11px 16px !important; font-weight:600;
}}
.molgrid {{ display:grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }}
.molcard {{ display:flex; flex-direction:column; align-items:center; gap:6px; }}
.mollabel {{ font-size:12px; color:#475467; text-align:center; }}
</style>
""", unsafe_allow_html=True)

# Header
header_left, _ = st.columns([6,1])
with header_left:
    try:
        st.image("logo.png", width=120)
    except Exception:
        pass
    st.markdown("<h1 style='margin:6px 0 0 0;'>Aurora BioLab</h1>", unsafe_allow_html=True)
    st.markdown("<div class='muted'>AI platform for accelerated molecular discovery and prioritization</div>", unsafe_allow_html=True)

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# Target selection
st.markdown("<div class='section-title'>Choose a target</div>", unsafe_allow_html=True)
targets = [
    "EGFR (non-small cell lung cancer)",
    "KRAS (pancreatic / lung / colorectal cancers)",
    "BRAF (melanoma)",
    "HER2 / ERBB2 (breast cancer)",
    "PD-1 / PDCD1 (oncology, immunotherapy)",
    "PD-L1 / CD274 (oncology, immunotherapy)",
    "VEGFA (angiogenesis, oncology)",
    "ALK (non-small cell lung cancer)",
    "BRCA1 (breast / ovarian cancer)",
    "PARP1 (ovarian cancer)"
]
target = st.selectbox("Target (protein / disease)", targets, index=0, label_visibility="collapsed")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# Databases
st.markdown("<div class='section-title'>Search across databases</div>", unsafe_allow_html=True)
st.text("ChEMBL\nBindingDB\nPubChem\nZINC\nUniProt\nPDB")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# Filters
st.markdown("<div class='section-title'>Filtering parameters</div>", unsafe_allow_html=True)
max_tox = st.slider("Toxicity threshold (0 = low, 1 = high)", 0.0, 1.0, 0.6, 0.05)
top_n   = st.slider("Number of candidates", 3, 10, 5, 1)

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# Instruction & button
st.info("Choose a target and run search")
st.markdown("<div class='primary-btn'>", unsafe_allow_html=True)
run = st.button("Run search")
st.markdown("</div>", unsafe_allow_html=True)
if run:
    st.session_state["run"] = True

# Demo data
def generate_demo(n=10, seed=42):
    random.seed(seed)
    rows = []
    for i in range(1, n+1):
        activity  = round(random.uniform(0.30, 0.95), 2)
        toxicity  = round(random.uniform(0.10, 0.80), 2)
        score     = max(0.0, min(1.0, activity * (1 - toxicity) * 1.25))
        label     = "priority" if (activity >= 0.7 and toxicity <= 0.5) else "reserve"
        rows.append({
            "Molecule": f"Mol-{i:03d}",
            "Activity": activity,
            "Toxicity": toxicity,
            "Composite score": round(score, 2),
            "Status": label
        })
    df = pd.DataFrame(rows).sort_values("Composite score", ascending=False).reset_index(drop=True)
    return df

# SVG molecule
def molecule_svg(name: str, size: int = 64, stroke="#111827") -> str:
    rng = random.Random(hash(name) % (10**7))
    cx, cy = size/2, size/2
    r = size*0.26
    rot = rng.uniform(0, math.pi/3)

    pts = []
    for k in range(6):
        theta = rot + k*(math.pi/3)
        x = cx + r*math.cos(theta)
        y = cy + r*math.sin(theta)
        pts.append((x, y))

    def line(x1,y1,x2,y2,w=1.6, col=stroke, cap="round"):
        return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{col}" stroke-width="{w}" stroke-linecap="{cap}" />'

    bg = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size*0.44:.1f}" fill="{A_TEAL}11" />'
    edges = [line(*pts[i], *pts[(i+1)%6], w=1.8) for i in range(6)]

    dbl = []
    for i in range(0,6,2):
        x1,y1 = pts[i]; x2,y2 = pts[(i+1)%6]
        dx, dy = x2-x1, y2-y1
        L = math.hypot(dx,dy) or 1
        ox, oy = -dy/L*2.0, dx/L*2.0
        dbl.append(line(x1+ox,y1+oy,x2+ox,y2+oy,w=1.2,col="#1F2937"))

    subs = []
    n_sub = random.Random(hash(name) % (10**6)).randint(1,3)
    for _ in range(n_sub):
        i = rng.randint(0,5)
        x1,y1 = pts[i]
        vx, vy = x1-cx, y1-cy
        L = math.hypot(vx,vy) or 1
        ux, uy = vx/L, vy/L
        L2 = size*0.24
        x3, y3 = x1+ux*L2, y1+uy*L2
        subs.append(line(x1,y1,x3,y3,w=1.5,col="#243045"))
        subs.append(f'<circle cx="{x3:.2f}" cy="{y3:.2f}" r="1.8" fill="#0F172A" />')

    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">{bg}{"".join(edges)}{"".join(dbl)}{"".join(subs)}</svg>'

def svg_card(name: str, size: int = 64) -> str:
    return f'<div class="molcard">{molecule_svg(name, size=size)}<div class="mollabel">{name}</div></div>'

# Results
if st.session_state.get("run"):
    started_at = time.strftime("%Y-%m-%d %H:%M")
    run_id = str(abs(hash(target)) % (10**6))

    with st.spinner("Running AI ranking and prioritization…"):
        time.sleep(0.9)

    df_all  = generate_demo(n=10, seed=hash(target) % (10**6))
    df_view = df_all[df_all["Toxicity"] <= max_tox].head(top_n)

    st.markdown("<div class='section-title'>Results</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='badges'><span>Target: {target}</span>"
        f"<span>toxicity ≤ {max_tox:.2f}</span><span>top {top_n}</span>"
        f"<span>run {run_id}</span><span>{started_at}</span></div>",
        unsafe_allow_html=True
    )

    # show index from 1
    df_disp = df_view.copy()
    df_disp.index = range(1, len(df_disp)+1)

    def color_rows(row):
        if row.name == 1: return [f"background-color: {ROW1_BG}; color: {PRIMARY};"] * len(row)
        if row.name == 2: return [f"background-color: {ROW2_BG}; color: {PRIMARY};"] * len(row)
        if row.name == 3: return [f"background-color: {ROW3_BG}; color: {PRIMARY};"] * len(row)
        return ["" for _ in row]

    styled = (
        df_disp.style
        .apply(color_rows, axis=1)
        .set_properties(subset=["Molecule"], **{"font-weight": "600"})
        .format({"Activity":"{:.2f}", "Toxicity":"{:.2f}", "Composite score":"{:.2f}"})
    )
    st.dataframe(styled, use_container_width=True, height=38 * (len(df_disp) + 1))

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Molecular visuals — SVG grid
    st.markdown("<div class='section-title'>Molecular visuals</div>", unsafe_allow_html=True)
    html = '<div class="molgrid">'
    for _, r in df_disp.iterrows():
        html += svg_card(r["Molecule"], size=64)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Charts with strictly vertical X labels (Altair)
    ch_df = df_disp.reset_index().rename(columns={"index":"#"})
    ch_df["#"] = ch_df["#"].astype(str)
    ch_df["Safety"] = 1 - ch_df["Toxicity"]

    def bar_chart(df, y_col, title):
        return (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(
                    '#:N',
                    axis=alt.Axis(
                        labelAngle=-90,
                        labelAlign='center',
                        labelBaseline='middle',
                        labelPadding=4,
                        title=None,
                        labelLimit=1000
                    )
                ),
                y=alt.Y(f'{y_col}:Q', axis=alt.Axis(title=None)),
                tooltip=['#', 'Molecule', 'Activity', 'Toxicity', 'Composite score']
            )
            .properties(height=220, title=title)
            .configure_title(font='Inter', fontSize=14, anchor='start', color=PRIMARY)
            .configure_axis(labelFont='Inter', titleFont='Inter')
            .configure_view(strokeWidth=0)
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.altair_chart(bar_chart(ch_df, 'Activity', 'Activity'), use_container_width=True)
    with c2:
        st.altair_chart(bar_chart(ch_df, 'Safety', 'Safety'), use_container_width=True)
    with c3:
        st.altair_chart(bar_chart(ch_df, 'Composite score', 'Composite score'), use_container_width=True)

    st.caption("Safety is computed from toxicity.")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Exports (CSV + PDF, stacked vertically)
    csv = df_disp.to_csv(index=True).encode("utf-8")
    st.download_button("Download table (CSV)", csv, file_name="aurora_candidates.csv", type="secondary")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm

        def build_pdf(title, target_name, df: pd.DataFrame) -> bytes:
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            W, H = A4

            c.setFont("Helvetica-Bold", 13)
            c.drawString(2*cm, H-2*cm, title)

            c.setFont("Helvetica", 10.5)
            c.drawString(2*cm, H-3*cm, f"Target: {target_name}")
            c.drawString(2*cm, H-3.6*cm, f"Toxicity ≤ {max_tox:.2f}; Top: {len(df)}; Run {run_id}; {started_at}")

            # table header
            y = H - 5*cm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1.5*cm, y, "#")
            c.drawString(2.5*cm, y, "Molecule")
            c.drawString(8.0*cm, y, "Activity")
            c.drawString(11.0*cm, y, "Toxicity")
            c.drawString(14.0*cm, y, "Composite")
            c.setFont("Helvetica", 10)
            y -= 0.7*cm

            for idx, (_, r) in enumerate(df.iterrows(), start=1):
                c.drawString(1.5*cm, y, str(idx))
                c.drawString(2.5*cm, y, str(r["Molecule"]))
                c.drawString(8.0*cm, y, f'{r["Activity"]:.2f}')
                c.drawString(11.0*cm, y, f'{r["Toxicity"]:.2f}')
                c.drawString(14.0*cm, y, f'{r["Composite score"]:.2f}')
                y -= 0.6*cm
                if y < 2*cm:
                    c.showPage()
                    y = H - 2*cm

            c.showPage()
            c.save()
            buf.seek(0)
            return buf.getvalue()

        pdf_bytes = build_pdf("Aurora BioLab — Candidate Shortlist", target, df_disp)
        st.download_button("Download report (PDF)", data=pdf_bytes, file_name="aurora_report.pdf", type="primary")
    except Exception:
        st.info("Install reportlab to enable PDF export: pip3 install reportlab")

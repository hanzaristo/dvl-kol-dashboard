import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
import re
import requests

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="Darya Varia Laboratoria KOL Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============ HIDE STREAMLIT TOOLBAR & GLOBAL TABLE STYLES ============
st.markdown("""
<style>
/* Hide only the deploy button / menu / toolbar actions, NOT the whole toolbar,
   so the sidebar re-open button stays available */
.stAppDeployButton {display: none;}
#MainMenu {visibility: hidden;}
[data-testid="stMainMenu"] {visibility: hidden;}
[data-testid="stToolbarActions"] {visibility: hidden;}

/* Make sure the "re-open sidebar" button is always visible
   (selector names differ between Streamlit versions, so all are listed) */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
}

.scrollable-table {
    width: 100%;
    overflow-x: auto;
    display: block;
    margin-bottom: 10px;
}
.scrollable-table table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.scrollable-table th, .scrollable-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #e0e0e0;
    white-space: nowrap;
}
.scrollable-table th {
    background-color: #f0f4f8;
    color: #1a3a5c;
    font-weight: bold;
    border-bottom: 2px solid #1a3a5c;
}
</style>
""", unsafe_allow_html=True)

# ============ CUSTOM COLORS ============
DARK_BLUE = "#1a3a5c"
LIGHT_BLUE = "#4a90d9"

# ============ CUT OFF DATE (edit this each month) ============
CUT_OFF_DATE = "30 September"

# ============ SIDEBAR WITH LOGO (TOP) ============
with st.sidebar:
    try:
        st.image("Logo_OM_x_DVL.png", use_container_width=True)
    except:
        st.markdown(f"""
        <div style="display: flex; justify-content: center; font-size: 60px; color: {DARK_BLUE};">
            📊
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; color: {DARK_BLUE}; font-size: 18px; font-weight: bold; margin-bottom: 20px;">
        Darya Varia Laboratoria<br>KOL Dashboard
    </div>
    """, unsafe_allow_html=True)

    st.divider()


# ============ LOAD DATA ============
@st.cache_data
def load_data():
    try:
        # utf-8-sig strips a UTF-8 BOM if present (common after Excel/GitHub
        # web-edit re-saves), which otherwise silently corrupts the FIRST
        # column name only (e.g. "Product" becomes "\ufeffProduct"),
        # making that one filter vanish while all others work fine.
        df = pd.read_csv('KOL Tracker Updated.csv', sep=';', encoding='utf-8-sig')
        return df
    except:
        try:
            df = pd.read_csv('KOL Tracker Updated.csv', sep=';', encoding='latin-1')
            return df
        except:
            st.error("❌ Could not load the file")
            st.info("Make sure 'KOL Tracker Updated.csv' is in the folder")
            return pd.DataFrame()


df = load_data()

if df.empty:
    st.stop()


# ============ REMOVE UNWANTED COLUMNS ============
# Remove "0,019918483" column if it exists
df = df.loc[:, ~df.columns.astype(str).str.contains('0,019918483', na=False)]


# ============ CLEAN COLUMN NAMES ============
df.columns = [
    str(col).replace('\ufeff', '').strip()
    .replace(' ', '_')
    .replace('/', '_')
    .replace('-', '_')
    .replace('(', '')
    .replace(')', '')
    .replace(',', '_')
    for col in df.columns
]

if 'Category.1' in df.columns:
    df = df.rename(columns={'Category': 'Product', 'Category.1': 'Category'})


# ============ FIX: PROPERLY HANDLE PRODUCT ============
has_product = any(col in df.columns for col in ['Product', 'product', 'Produk', 'produk', 'PRODUCT'])

if has_product:
    product_columns = ['Product', 'product', 'Produk', 'produk', 'PRODUCT', 'Product_Name', 'product_name']
    for col in df.columns:
        if col in product_columns:
            df = df.rename(columns={col: 'Product'})
            break
elif not has_product and len(df.columns) > 0:
    first_col = df.columns[0]
    if (df[first_col].dtype == 'object' and
            first_col not in ['KOL_Name', 'Platform', 'Tier', 'Brands', 'Sub_Brands', 'Objective', 'Link_Post', 'Month', 'Category']):
        df = df.rename(columns={first_col: 'Product'})

if 'Product' in df.columns:
    df['Product'] = df['Product'].astype(str).str.strip()


# ============ CLEAN PLATFORM NAMES ============
if 'Platform' in df.columns:
    df['Platform'] = df['Platform'].astype(str).str.strip()
    df['Platform'] = df['Platform'].str.replace('Tiktok', 'TikTok', case=False)
    df['Platform'] = df['Platform'].str.replace('tiktok', 'TikTok', case=False)
    df['Platform'] = df['Platform'].str.replace('x', 'X', case=False)
    df['Platform'] = df['Platform'].str.replace('instagram', 'Instagram', case=False)
    df['Platform'] = df['Platform'].str.strip()


# ============ CLEAN TIER NAMES ============
if 'Tier' in df.columns:
    df['Tier'] = df['Tier'].astype(str).str.strip()
    df['Tier'] = df['Tier'].str.capitalize()


# ============ CLEAN CATEGORY NAMES ============
if 'Category' in df.columns:
    df['Category'] = df['Category'].astype(str).str.strip()


# ============ CLEAN SUB-BRANDS AND BRANDS ============
if 'Sub_Brands' in df.columns:
    df['Sub_Brands'] = df['Sub_Brands'].astype(str).str.strip()

if 'Brands' in df.columns:
    df['Brands'] = df['Brands'].astype(str).str.strip()


# ============ CONVERT DATA TYPES ============
currency_count_cols = [
    'Followers_Number',
    'Actual_Spends_IDR',
    'Reach',
    'Views',
    'Likes',
    'Comments',
    'Share',
    'CPV_Rp'
]

for col in currency_count_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace('Rp', '', regex=False)
            .str.replace('%', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors='coerce')


percent_cols = [
    'ER',
    'ER_Views',
    'VR'
]

for col in percent_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace('%', '')
            .str.replace(',', '')
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors='coerce')


# ============ FIX: CLEAN AND VALIDATE MONTHS ============
if 'Month' in df.columns:
    df['Month'] = df['Month'].astype(str).str.strip()

    valid_months = [
        'Jan-26',
        'Feb-26',
        'Mar-26',
        'Apr-26',
        'May-26',
        'Jun-26',
        'Jul-26',
        'Aug-26',
        'Sep-26',
        'Oct-26'
    ]

    df = df[df['Month'].isin(valid_months)]

    df['Month'] = pd.to_datetime(df['Month'], format='%b-%y')


# ============ HELPER FUNCTION TO CLEAN KOL NAME ============
def clean_kol_name(name):
    """Remove numbers/prefixes before KOL name and clean up"""
    if pd.isna(name):
        return name

    name = str(name).strip()
    name = re.sub(r'^\d+\s+', '', name)
    name = re.sub(r'^\d+', '', name)
    name = name.strip()
    name = name.replace('\u200b', '').replace('\u00a0', ' ')
    name = re.sub(r'\s+', ' ', name)

    return name


# ============ APPLY CLEAN KOL NAME TO DATAFRAME ============
if 'KOL_Name' in df.columns:
    df['KOL_Name_Original'] = df['KOL_Name']
    df['KOL_Name'] = df['KOL_Name'].apply(clean_kol_name)


# ============ SIDEBAR FILTERS (WITH MULTISELECT) ============
with st.sidebar:
    st.subheader("Filters")

    filtered_df = df.copy()

    # ============ FILTER BY MONTH ============
    if 'Month' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Month']):
        unique_months = df['Month'].unique()
        sorted_months_dt = sorted(unique_months)
        sorted_months = [pd.Timestamp(dt).strftime('%b-%y') for dt in sorted_months_dt]

        month_options = ['Select All'] + sorted_months

        selected_months = st.multiselect(
            "Select Months",
            options=month_options,
            default=['Select All']
        )

        if 'Select All' in selected_months:
            selected_months = sorted_months

        if selected_months:
            filtered_df = filtered_df[
                filtered_df['Month'].dt.strftime('%b-%y').isin(selected_months)
            ]

    # ============ FILTER BY TIER ============
    if 'Tier' in df.columns:
        tier_options = ['Select All'] + sorted(df['Tier'].dropna().unique().tolist())

        selected_tiers = st.multiselect(
            "Select Tiers",
            options=tier_options,
            default=['Select All']
        )

        if 'Select All' in selected_tiers:
            selected_tiers = sorted(df['Tier'].dropna().unique().tolist())

        if selected_tiers:
            filtered_df = filtered_df[filtered_df['Tier'].isin(selected_tiers)]

    # ============ FILTER BY SUB-BRAND ============
    if 'Sub_Brands' in df.columns:
        sub_brands_options = ['Select All'] + sorted(df['Sub_Brands'].dropna().unique().tolist())

        selected_sub_brands = st.multiselect(
            "Select Sub Brands",
            options=sub_brands_options,
            default=['Select All']
        )

        if 'Select All' in selected_sub_brands:
            selected_sub_brands = sorted(df['Sub_Brands'].dropna().unique().tolist())

        if selected_sub_brands:
            filtered_df = filtered_df[filtered_df['Sub_Brands'].isin(selected_sub_brands)]

    # ============ FILTER BY BRAND ============
    if 'Brands' in df.columns:
        brands_options = ['Select All'] + sorted(df['Brands'].dropna().unique().tolist())

        selected_brands = st.multiselect(
            "Select Brands",
            options=brands_options,
            default=['Select All']
        )

        if 'Select All' in selected_brands:
            selected_brands = sorted(df['Brands'].dropna().unique().tolist())

        if selected_brands:
            filtered_df = filtered_df[filtered_df['Brands'].isin(selected_brands)]

    # ============ FILTER BY CATEGORY (sourced from Product column) ============
    if 'Product' in df.columns:
        product_options = ['Select All'] + sorted(df['Product'].dropna().unique().tolist())

        selected_products = st.multiselect(
            "Select Category",
            options=product_options,
            default=['Select All']
        )

        if 'Select All' in selected_products:
            selected_products = sorted(df['Product'].dropna().unique().tolist())

        if selected_products:
            filtered_df = filtered_df[filtered_df['Product'].isin(selected_products)]

    # ============ CLEAR ALL FILTERS ============
    if st.button("🔄 Clear All Filters", use_container_width=True):
        st.rerun()


# ============ FORMATTING FUNCTIONS ============
def format_number(num):
    if pd.isna(num) or num == 0:
        return "0"

    num = float(num)

    if num >= 1_000_000_000:
        val = num / 1_000_000_000
        return f"{val:.1f}B".replace('.0B', 'B')
    elif num >= 1_000_000:
        val = num / 1_000_000
        return f"{val:.1f}M".replace('.0M', 'M')
    elif num >= 1_000:
        val = num / 1_000
        return f"{val:.1f}K".replace('.0K', 'K')
    else:
        return f"{num:,.0f}"


def format_currency(num):
    if pd.isna(num) or num == 0:
        return "Rp 0"

    num = float(num)

    if num >= 1_000_000_000:
        val = num / 1_000_000_000
        return f"Rp {val:.1f}B".replace('.0B', 'B')
    elif num >= 1_000_000:
        val = num / 1_000_000
        return f"Rp {val:.1f}M".replace('.0M', 'M')
    elif num >= 1_000:
        val = num / 1_000
        return f"Rp {val:.1f}K".replace('.0K', 'K')
    else:
        return f"Rp {num:,.0f}"


def format_percent(num):
    if pd.isna(num):
        return "0%"

    if num <= 1:
        num = num * 100

    formatted = f"{num:.2f}%"
    formatted = formatted.replace('.00%', '%')

    if '.' in formatted:
        while formatted.endswith('0%'):
            formatted = formatted[:-2] + '%'

        if formatted.endswith('.%'):
            formatted = formatted[:-2] + '%'

    return formatted


def format_currency_short(num):
    if pd.isna(num) or num == 0:
        return "Rp 0"

    return f"Rp {num:,.2f}"


# ============ BAR CHART FUNCTIONS ============
def create_bar_chart(data, x_col, y_col, color=None):
    df_chart = data.reset_index()
    df_chart.columns = [x_col, y_col]

    bars = alt.Chart(df_chart).mark_bar(
        color=color if color else DARK_BLUE,
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4
    ).encode(
        x=alt.X(
            x_col + ':O',
            axis=alt.Axis(labels=True, title=None, labelAngle=0),
            sort=None
        ),
        y=alt.Y(
            y_col + ':Q',
            axis=alt.Axis(labels=False, title=None, grid=False)
        ),
        tooltip=[
            x_col,
            alt.Tooltip(y_col, format=',.0f')
        ]
    )

    text = alt.Chart(df_chart).mark_text(
        align='center',
        baseline='bottom',
        dy=-10,
        fontSize=13,
        fontWeight='bold',
        color=DARK_BLUE
    ).encode(
        x=alt.X(x_col + ':O', sort=None),
        y=alt.Y(y_col + ':Q'),
        text=alt.Text(y_col + ':Q', format=',.0f')
    )

    chart = (bars + text).properties(
        width='container',
        height=350
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelFontSize=12,
        labelColor='#666',
        grid=False
    )

    return chart


def create_stacked_bar_chart(data, category_col, category_order, colors, month_order_str):
    # Hide labels on narrow segments (< 5%) so they never overlap when zoomed
    text_data = data[data['Percentage'] >= 5].copy()

    bars = alt.Chart(data).mark_bar(
        cornerRadiusTopRight=2,
        cornerRadiusBottomRight=2
    ).encode(
        y=alt.Y(
            'Month_Str:O',
            title=None,
            sort=month_order_str,
            axis=alt.Axis(labels=True, labelAngle=0)
        ),
        x=alt.X(
            'Segment_Start:Q',
            title=None,
            axis=alt.Axis(labels=False)
        ),
        x2=alt.X2('Segment_End:Q'),
        color=alt.Color(
            f'{category_col}:N',
            legend=alt.Legend(
                title=None,
                orient='right',
                labelFontSize=11,
                labelLimit=150,
                labelPadding=10,
                rowPadding=5
            ),
            scale=alt.Scale(domain=category_order, range=colors)
        ),
        tooltip=[
            alt.Tooltip('Month_Str:O', title='Month'),
            alt.Tooltip(f'{category_col}:N', title=category_col),
            alt.Tooltip('Actual_Spends_IDR:Q', format=',.0f', title='Spend'),
            alt.Tooltip('Percentage:Q', format='.0f', title='%')
        ]
    )

    text = alt.Chart(text_data).mark_text(
        align='center',
        baseline='middle',
        fontSize=10,
        fontWeight='bold',
        color='white'
    ).encode(
        y=alt.Y('Month_Str:O', sort=month_order_str),
        x=alt.X('Label_Position:Q'),
        text=alt.Text('Percentage_Label:N')
    )

    return alt.layer(bars, text).properties(
        width='container',
        height=300
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelFontSize=12,
        labelColor='#666',
        grid=False
    )


# ============ HEADER STYLE FUNCTIONS ============
def section_header_with_divider(title):
    st.divider()
    st.markdown(f"""
    <div style="color: #000000; font-size: 24px; font-weight: bold; margin-bottom: 15px; margin-top: 10px;">
        {title}
    </div>
    """, unsafe_allow_html=True)


def section_header_no_divider(title):
    st.markdown(f"""
    <div style="color: #000000; font-size: 24px; font-weight: bold; margin-bottom: 15px; margin-top: 10px;">
        {title}
    </div>
    """, unsafe_allow_html=True)


def section_header_with_cutoff(title, cutoff_text):
    st.markdown(f"""
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        margin-top: 10px;
    ">
        <div style="color: #000000; font-size: 24px; font-weight: bold;">
            {title}
        </div>
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #eef3f9;
            color: {DARK_BLUE};
            border: 1px solid #d0d7e2;
            border-left: 3px solid {LIGHT_BLUE};
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.3px;
            white-space: nowrap;
        ">
            📅 {cutoff_text}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============ LINK PREVIEW: THUMBNAIL FETCH + HOVER CARD ============
@st.cache_data(ttl=86400, show_spinner=False)
def get_video_thumbnail(url):
    """Return a preview thumbnail URL for a social post link, where the platform allows it."""
    if pd.isna(url) or not str(url).strip():
        return None

    url = str(url).strip()

    try:
        if 'tiktok.com' in url:
            resp = requests.get(
                'https://www.tiktok.com/oembed',
                params={'url': url},
                timeout=3
            )
            if resp.ok:
                return resp.json().get('thumbnail_url')
    except Exception:
        return None

    return None


st.markdown("""
<style>
.link-preview-wrap {
    position: relative;
    display: inline-block;
}
.link-preview-wrap .preview-img {
    display: none;
    position: absolute;
    z-index: 999;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-bottom: 6px;
    width: 160px;
    border-radius: 8px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.25);
    border: 2px solid #fff;
}
.link-preview-wrap:hover .preview-img {
    display: block;
}
</style>
""", unsafe_allow_html=True)


def make_clickable_with_preview(link):
    """Clickable 'View Post' link with a hover thumbnail (TikTok only)."""
    if pd.isna(link) or link == '':
        return ''

    thumb = get_video_thumbnail(link)

    link_html = (
        f'<a href="{link}" target="_blank" '
        f'style="color: {DARK_BLUE}; '
        f'text-decoration: none; '
        f'font-weight: bold;">'
        f'🔗 View Post</a>'
    )

    if thumb:
        return (
            f'<span class="link-preview-wrap">'
            f'{link_html}'
            f'<img class="preview-img" src="{thumb}" referrerpolicy="no-referrer">'
            f'</span>'
        )

    return link_html


# ============ CALCULATE CPV ============
if (
    'Actual_Spends_IDR' in filtered_df.columns
    and 'Views' in filtered_df.columns
):
    filtered_df['CPV_Calculated'] = (
        filtered_df['Actual_Spends_IDR']
        / filtered_df['Views']
    )

    filtered_df['CPV_Calculated'] = (
        filtered_df['CPV_Calculated']
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )


# ============ CALCULATE KPIS ============
total_views = (
    filtered_df['Views'].sum()
    if 'Views' in filtered_df.columns
    else 0
)

total_engagement = (
    filtered_df['Likes'].sum()
    + filtered_df['Comments'].sum()
    + filtered_df['Share'].sum()
    if all(
        col in filtered_df.columns
        for col in ['Likes', 'Comments', 'Share']
    )
    else 0
)

total_spend = (
    filtered_df['Actual_Spends_IDR'].sum()
    if 'Actual_Spends_IDR' in filtered_df.columns
    else 0
)

total_reach = (
    filtered_df['Reach'].sum()
    if 'Reach' in filtered_df.columns
    else 0
)


# ============ FIXED KOL COUNT ============
if 'KOL_Name' in filtered_df.columns:
    kol_cleaned = filtered_df['KOL_Name'].astype(str).str.strip()
    kol_cleaned = kol_cleaned.str.replace(r'\s+', ' ', regex=True)
    kol_cleaned = kol_cleaned.str.replace('\u200b', '', regex=False)
    kol_cleaned = kol_cleaned.str.replace('\u00a0', ' ', regex=False)
    kol_cleaned = kol_cleaned.str.lower()
    total_kols = kol_cleaned.nunique()
else:
    total_kols = 0


total_posts = len(filtered_df)


# ============ FIXED ER CALCULATION ============
if (
    'Followers_Number' in filtered_df.columns
    and filtered_df['Followers_Number'].sum() > 0
):
    engagement_rate = total_engagement / filtered_df['Followers_Number'].sum()
else:
    engagement_rate = 0


avg_cpv = (
    filtered_df['Actual_Spends_IDR'].sum() / filtered_df['Views'].sum()
    if 'Actual_Spends_IDR' in filtered_df.columns
    and 'Views' in filtered_df.columns
    and filtered_df['Views'].sum() > 0
    else 0
)


# ============ KPI METRICS - ROW 1 ============
section_header_with_cutoff(
    "Overall Performance",
    f"Cut Off Date: {CUT_OFF_DATE}"
)

st.markdown("""
<style>
.kpi-card {
    border: 1.5px solid #d0d7e2;
    border-radius: 10px;
    padding: 16px 12px;
    margin: 5px 0;
    background: linear-gradient(135deg, #fafbfc 0%, #ffffff 100%);
    box-shadow: 0 1px 3px rgba(26, 58, 92, 0.06);
    transition: all 0.25s ease;
    height: 100%;
    position: relative;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #1a3a5c, #4a90d9);
    border-radius: 10px 10px 0 0;
    opacity: 0.6;
}
.kpi-card:hover {
    box-shadow: 0 4px 12px rgba(26, 58, 92, 0.10);
    border-color: #b0c0d0;
    transform: translateY(-1px);
}
.kpi-label {
    margin-bottom: 2px;
    color: #1a3a5c;
    font-size: 13px;
    text-align: center;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.kpi-value {
    font-size: 24px;
    font-weight: 600;
    margin-top: 2px;
    text-align: center;
    color: #1a3a5c;
    letter-spacing: -0.5px;
}
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Views</p>
        <p class="kpi-value">{format_number(total_views)}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Reach</p>
        <p class="kpi-value">{format_number(total_reach)}</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Engagement</p>
        <p class="kpi-value">{format_number(total_engagement)}</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Spend</p>
    

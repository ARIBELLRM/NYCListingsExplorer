"""
Name:       Ariana Ramirez
CS230:      Section 4
Data:       New York Housing Market
URL:        Link to your web application on Streamlit Cloud (if posted)


Description: This program was designed as a user-friendly website to help people who are looking for a new property on sale in New York. Users can:
            - Analyze the market: We provide interactive filters that show average prices and price ranges by sublocality, bedroom count, and property type.
            - Compare Brokers: Our website provides a chart to explore your preferred broker's listings.
            - Maps: We added both a PyDeck Map and a Folium overlay that display each listing along its price and address.
            - Visuals for data analysis: Matplotlib and Seaborn visuals show the overall price distribution, price-by-bedroom box-plots, and a beds-vs-price scatter, while an Altair bar chart ranks property types.
            For our interface, we chose to use a Gossip Girl's Manhattan luxury aesthetic with some gold accents, Times New Roman typography, and a skyline photo. To design the interface we used Pandas for the cleaning, Altair styles, PyDeck for the Google Map layer, and folium to add an interactive sample map."""

#-------Importing Python Packages--------------
import streamlit as st
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from streamlit_folium import st_folium
from pathlib import Path
import altair as alt

GOLD = "#C5A880"

#------Website Formatting-------------

st.set_page_config(
    page_title="NYC Listings Explorer",
    layout="wide",
    page_icon="🗽",
)

LOGO_URL_LARGE = "https://i.pinimg.com/736x/6b/a1/19/6ba119a25e6b5b63ca570bb90cc6774d.jpg"
st.logo(LOGO_URL_LARGE, link=LOGO_URL_LARGE) #ST4: Custom Logo

with st.sidebar:
    st.image(
        "https://static1.squarespace.com/static/5d0590f0e62d0e00018db3b7/"
        "5d059101775d2900010d4caa/633f1087c2e5ed6ad43f03eb/"
        "1682619528061/unsplash-image-1KPfcPdbWFM.jpg?format=1500w",
        use_container_width=True, #ST4: Custom Image
    )

#-----------CSS: To style font and graphs--------------------------------ST4: Custom Design
st.markdown(
    f"""
    <style>
        html, body, [class*="st-"] {{
            font-family:'Times New Roman',Times,serif!important;
            color:#000!important;
        }}
        section[data-testid="stSidebar"] {{ background:{GOLD}; }}
        section[data-testid="stSidebar"] * {{ color:#000!important; }}

        input[type="range"]::-webkit-slider-runnable-track,
        input[type="range"]::-moz-range-track {{ background:#FFF!important;height:4px; }}

        input[type="range"]::-webkit-slider-thumb,
        input[type="range"]::-moz-range-thumb {{
            background:#FFF!important;border:2px solid {GOLD}!important;
            height:18px;width:18px;border-radius:50%;margin-top:-7px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------Loading data and cleaning it [DA1]-----------------
st.header("NYC Listings Explorer 🏙️")
DATA_PATH = "/Users/ari.ramirezzz/PycharmProjects/PythonProject2/.venv/NY-House-Dataset.csv"
df = pd.read_csv(DATA_PATH)

df["PRICE"]     = pd.to_numeric(df["PRICE"], errors="coerce")
df["LATITUDE"]  = pd.to_numeric(df["LATITUDE"], errors="coerce")
df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

df["PRICE"] = (
    df["PRICE"].replace(r"[^\d.]", "", regex=True).astype(float, errors="ignore")
)
df = df[df["PRICE"].between(10_000, 100_000_000)] #[DA4] Filter by one condition
st.success(f"Loaded **{len(df):,}** listings.")


# ------Helper Functions: Average + price range
def avg_price_by_city(df, city, beds=2): #PY1
    mask = (
        df["SUBLOCALITY"].str.strip().str.lower() == city.strip().lower()
    ) & (df["BEDS"] == beds)
    return df.loc[mask, "PRICE"].mean()
def price_range(df, city, beds): #PY2
    subset = df[
        (df["SUBLOCALITY"].str.strip().str.lower() == city.strip().lower())
        & (df["BEDS"] == beds)
    ]
    return subset["PRICE"].min(), subset["PRICE"].max()

#---------Key Metrics----------------------------
st.header("Key metrics:")
manhattan_1br_condos = df.loc[ #[DA5] Filter by ≥ 2 conditions (AND)
    (df["SUBLOCALITY"].str.strip().str.lower() == "manhattan")
    & (df["BEDS"] == 1)
    & df["TYPE"].str.contains(r"\bcondo\b", case=False, na=False)
]
condo_count = df["TYPE"].str.contains(r"\bcondo\b", case=False, na=False).sum()
avg_price_manh = manhattan_1br_condos["PRICE"].mean()

col1, col2 = st.columns(2)
col1.metric("Avg price · 1-BR Manhattan condo",
            f"${avg_price_manh:,.0f}" if pd.notna(avg_price_manh) else "N/A")
col2.metric("Total condos in file", f"{condo_count:,}")

with st.expander("See 1-BR Manhattan condos"):
    st.dataframe(manhattan_1br_condos[["PRICE", "ADDRESS", "TYPE"]]) #Data Table

# ------Sidebar Filters: Average price lookup + default 2bd avg----------

st.sidebar.header("Average-price lookup")

city_options = sorted(df["SUBLOCALITY"].str.strip().unique())
sel_city = st.sidebar.selectbox("Choose a city / borough:", city_options) #ST1:selectbox

sel_beds = st.sidebar.slider(
    "Number of bedrooms", int(df["BEDS"].min()), int(df["BEDS"].max()), 2, 1 #ST2: Slider
)

lookup_avg = avg_price_by_city(df, sel_city, sel_beds) #PY1
if pd.isna(lookup_avg):
    st.sidebar.write("No listings match.")
else:
    st.sidebar.write(f"Average price: **${lookup_avg:,.0f}**")

try: #PY3
    default_avg = avg_price_by_city(df, sel_city)          # PY1: Uses Default
    if sel_beds != 2 and pd.notna(default_avg):
        st.sidebar.caption(f"Default 2-BR avg: ${default_avg:,.0f}")
except Exception as e:
    st.sidebar.warning(f"Lookup error: {e}")

#---------Sidebar-Property Type Breakdown-----------

st.sidebar.header("Listings by property type")
type_df = (
    pd.DataFrame(df["TYPE"].value_counts().items(),#PY5
                 columns=["Property type", "Listings"])
       .sort_values("Listings", ascending=False) #DA2 Sort Rows
)
bar_chart = (
    alt.Chart(type_df)
       .mark_bar(color=GOLD)
       .encode(x=alt.X("Property type:N", sort="-y",
                       axis=alt.Axis(labelAngle=-40)),
               y="Listings:Q")
       .properties(height=250)
)
st.sidebar.altair_chart(bar_chart, use_container_width=True)

# ----------Broker Explorer-------------------

st.header("Broker explorer 🏢")

df["BROKER_CLEAN"] = ( #[DA7] Add / select columns
    df["BROKERTITLE"]
      .str.replace(r"^Brokered by\s+", "", regex=True)
      .str.strip()
)
broker_options  = ["< All brokers >"] + sorted(df["BROKER_CLEAN"].unique())
selected_broker = st.selectbox("Select a broker:", broker_options) #ST1: Selectbox

broker_df = (
    df if selected_broker == "< All brokers >"
    else df[df["BROKER_CLEAN"] == selected_broker]
).copy()
st.metric("Total properties", len(broker_df))

if selected_broker != "< All brokers >":
    st.subheader(f"Properties brokered by **{selected_broker}**")
    st.dataframe(broker_df[["PRICE", "BEDS", "TYPE", "ADDRESS"]],
                 use_container_width=True)

# ---------Brooklyn Houses Table---------------

st.header("Brooklyn houses for sale 🏠")
brooklyn_houses = df.loc[
    df["SUBLOCALITY"].str.strip().str.lower().eq("brooklyn")
    & df["TYPE"].str.contains(r"\bhouse\b", case=False, na=False)
    & ~df["TYPE"].str.contains(r"\btownhouse\b", case=False, na=False)
]
st.dataframe(brooklyn_houses[["PRICE", "BEDS", "TYPE", "ADDRESS"]],
             use_container_width=True)
#------Top 10 most expensive listings[DA3]-----------
top10 = df.nlargest(10, "PRICE")[["PRICE", "TYPE", "ADDRESS", "SUBLOCALITY"]]
st.sidebar.header("Top-10 most expensive listings")
st.sidebar.dataframe(top10)

# ------------Maps----------------------
st.header("Interactive map 🗺️")

# ---- sidebar filters ----
st.sidebar.header("Map filters")
boroughs_all  = sorted(df["SUBLOCALITY"].str.strip().unique())
sel_boroughs  = st.sidebar.multiselect("Borough / County", boroughs_all,
                                       default=["Brooklyn"]) #ST3: Multiselect

kw_text = st.sidebar.text_input("Property-type keyword(s)", value="house")
bed_min, bed_max = st.sidebar.slider("Bedrooms", #ST2
                                     int(df["BEDS"].min()),
                                     int(df["BEDS"].max()),
                                     (1, 4))
price_min, price_max = int(df["PRICE"].min()), int(df["PRICE"].max())
price_lo, price_hi = st.sidebar.slider("Price range ($)", #ST2
                                       price_min, price_max,
                                       (price_min, price_max),
                                       step=10_000, format="$%d") #PY2

keywords = [k.strip().lower() for k in kw_text.split(",") if k.strip()] #PY4
mask = ( #[DA5] Filter by ≥ 2 conditions
    df["SUBLOCALITY"].str.strip().isin(sel_boroughs)
    & df["BEDS"].between(bed_min, bed_max)
    & df["PRICE"].between(price_lo, price_hi)
    & df["TYPE"].str.lower().apply(lambda t: any(k in t for k in keywords))
)
map_df = df.loc[mask].copy()
map_df["PRICE_STR"] = map_df["PRICE"].apply(lambda p: f"${p:,.0f}") #[DA9] New column / column math

st.subheader(f"Listings on map: {len(map_df)}")
if map_df.empty:
    st.info("No listings match the current filters.")
else:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[LONGITUDE, LATITUDE]",
        get_radius=60,
        get_fill_color=[30, 144, 255, 160],
        pickable=True,
    )
    view_state = pdk.ViewState(
        latitude=map_df["LATITUDE"].mean(),
        longitude=map_df["LONGITUDE"].mean(),
        zoom=11,
        pitch=45,
    )
    tooltip = {
        "html": "<b>{ADDRESS}</b><br>{PRICE_STR} · {BEDS} BR<br>{TYPE}",
        "style": {"backgroundColor": "white", "color": "black"},
    }
    st.pydeck_chart( #[MAP] Detailed interactive map
        pdk.Deck(layers=[layer],
                 initial_view_state=view_state,
                 map_provider="mapbox",
                 map_style="mapbox://styles/mapbox/streets-v12",
                 tooltip=tooltip)
    )

# ---------Extras----------------------
st.header("Additional visual insights:")

tab1, tab2, tab3, tab4 = st.tabs(["Price distributions", "Beds vs. price", "Folium map","Average price by locality and beds"])

with tab1:
    st.subheader("Listing-price histogram")
    fig_hist, ax_hist = plt.subplots()
    ax_hist.hist( #CHART1:Matplotlib histogram
        df["PRICE"] / 1_000_000,
        bins=40,
        color=GOLD,
        edgecolor="white"
    )

    ax_hist.set_title("Distribution of listing prices (millions USD)")
    ax_hist.set_xlabel("Price ($ million)")
    ax_hist.set_ylabel("Count")
    st.pyplot(fig_hist)

    st.subheader("Price distribution by bedroom count")
    fig_box, ax_box = plt.subplots()
    sns.boxplot(data=df, #[SEA1] Seaborn chart
                x="BEDS",
                y="PRICE",
                ax=ax_box,
                color=GOLD)
    ax_box.set_xlabel("Bedrooms")
    ax_box.set_ylabel("Price ($)")
    st.pyplot(fig_box)

with tab2:
    st.subheader("Beds vs. price scatter")
    fig_scatter, ax_scatter = plt.subplots()
    ax_scatter.scatter(df["BEDS"], #CHART 2: Matplotlib scatter
                       df["PRICE"] / 1_000,
                       alpha=0.4,
                       color=GOLD)
    ax_scatter.set_title("Beds vs. price")
    ax_scatter.set_xlabel("Bedrooms")
    ax_scatter.set_ylabel("Price ($ thousand)")
    st.pyplot(fig_scatter)

with tab3:
    st.subheader("Folium map: sample of listings")
    sample = df.sample(n=min(500, len(df)), random_state=1)
    fmap = folium.Map(location=[sample["LATITUDE"].mean(),
                                sample["LONGITUDE"].mean()],
                      zoom_start=11, tiles="cartodbpositron")

    for _, row in sample.iterrows(): #[DA8] Iterate rows (iterrows)
        folium.CircleMarker( #[FOLIUM1] :Map
            [row["LATITUDE"], row["LONGITUDE"]],
            radius=4,
            color=GOLD,
            fill=True, fill_color=GOLD, fill_opacity=0.8,
            tooltip=f'{row["ADDRESS"]}<br>${row["PRICE"]:,.0f}'
        ).add_to(fmap)

    st_folium(fmap, height=500, width="100%") #[FOLIUM2]

with tab4: #D6 Pivot Table
    piv = df.pivot_table(values="PRICE",
                         index="SUBLOCALITY",
                         columns="BEDS",
                         aggfunc="mean").round(0)
    st.subheader("Average price by sublocality & bedrooms")
    st.dataframe(piv)

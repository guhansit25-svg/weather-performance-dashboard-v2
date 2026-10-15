import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(
    page_title="Weather DB Performance",
    page_icon="🌦️",
    layout="wide"
)

st.title("🌦️ Weather Database Performance Dashboard")
st.caption("Open-Meteo | Neon PostgreSQL | Index Benchmark")

# Actual benchmark results measured earlier
without_index = {
    "Average": 40.022,
    "Median": 39.920,
    "Fastest": 39.621,
    "Slowest": 41.188
}

with_index = {
    "Average": 37.942,
    "Median": 37.840,
    "Fastest": 37.474,
    "Slowest": 39.083
}

improvement = (
    (without_index["Average"] - with_index["Average"])
    / without_index["Average"] * 100
)

a, b, c = st.columns(3)
a.metric("Average without index", "40.022 ms")
b.metric("Average with index", "37.942 ms")
c.metric("Observed reduction", f"{improvement:.2f}%")

results = pd.DataFrame({
    "Metric": ["Average", "Median", "Fastest", "Slowest"],
    "Without index (ms)": list(without_index.values()),
    "With index (ms)": list(with_index.values())
})

st.subheader("Benchmark comparison")
st.dataframe(results, use_container_width=True, hide_index=True)
st.bar_chart(results.set_index("Metric"))

st.caption(
    "Each test used 30 measured runs and returned 120 rows. "
    "The observed difference does not prove the index alone caused "
    "the improvement."
)

st.divider()
st.subheader("Live Neon PostgreSQL data")

@st.cache_data(ttl=30)
def load_data():
    url = st.secrets["DATABASE_URL"]

    with psycopg2.connect(url) as conn:
        readings = pd.read_sql_query(
            """
            SELECT id, city, temperature, humidity, recorded_at
            FROM public.performance_test
            ORDER BY recorded_at DESC
            LIMIT 200;
            """,
            conn
        )

        indexes = pd.read_sql_query(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'performance_test';
            """,
            conn
        )

    return readings, indexes

if st.button("Refresh database data"):
    st.cache_data.clear()
    st.rerun()

try:
    readings, indexes = load_data()

    x, y = st.columns(2)
    x.metric("Records loaded", len(readings))
    y.metric(
        "Timestamp index",
        "Present" if
        "idx_performance_test_recorded_at"
        in indexes["indexname"].values else "Not found"
    )

    st.subheader("Latest weather records")
    if readings.empty:
        st.info("No records found in the database.")
    else:
        st.dataframe(
            readings,
            use_container_width=True,
            hide_index=True
        )

        chart = readings.dropna(subset=["temperature"])
        if not chart.empty:
            chart = chart.sort_values("recorded_at")
            st.subheader("Temperature readings")
            st.line_chart(
                chart.set_index("recorded_at")["temperature"]
            )

    st.subheader("Database indexes")
    st.dataframe(indexes, use_container_width=True, hide_index=True)

except Exception as error:
    st.error("Unable to connect to Neon. Check Streamlit Secrets.")
    st.code(str(error))

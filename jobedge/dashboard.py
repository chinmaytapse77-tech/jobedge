"""JobEdge dashboard. Read-only from storage -- never fetches, scores, or
writes anything. Run with: streamlit run jobedge/dashboard.py
"""

from __future__ import annotations

import streamlit as st

from jobedge.config import load_config
from jobedge import storage

TRACK_LABELS = {"sales": "Sales", "hr": "HR / Admin"}


@st.cache_resource
def _config():
    return load_config()


def main() -> None:
    st.set_page_config(page_title="JobEdge", layout="wide")
    st.title("JobEdge")
    st.caption("Live-scored listings and skill-gap report, per track. Read-only.")

    config = _config()
    tabs = st.tabs([TRACK_LABELS[p.name] for p in config.profiles])

    for tab, profile in zip(tabs, config.profiles):
        with tab:
            _render_track(config, profile.name)


def _render_track(config, profile_name: str) -> None:
    st.subheader("Skill gap report")
    st.caption("Skills you don't have yet, ranked by how many listings they'd unlock.")
    gaps = storage.get_skill_gaps(config.db_path, profile_name, limit=10)
    if gaps:
        st.dataframe(
            [{"Skill": g["skill"], "Listings it would unlock": g["frequency"]} for g in gaps],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No skill gaps found yet -- run more cycles, or nothing's missing for this pool.")

    st.subheader("Opportunity feed")
    st.caption(
        f"Showing matches posted within the last {config.max_listing_age_hours} hours, "
        f"asking for no more than about {config.max_years_experience} years of experience."
    )
    listings = storage.get_listings(
        config.db_path,
        profile_name,
        limit=100,
        min_score=config.min_fit_score,
        max_age_hours=config.max_listing_age_hours,
    )
    if not listings:
        older_count = len(
            storage.get_listings(config.db_path, profile_name, limit=100, min_score=config.min_fit_score)
        )
        if older_count:
            st.info(
                f"No listings posted within the last {config.max_listing_age_hours} hours yet, "
                f"though {older_count} older or undated match(es) exist."
            )
        else:
            st.info(f"No listings scoring at or above {config.min_fit_score} yet.")
        return

    st.dataframe(
        [
            {
                "Fit score": row["fit_score"],
                "Role": row["title"],
                "Company": row["company"],
                "Location": row["location"],
                "Why": row["fit_reason"],
                "Apply": row["url"],
            }
            for row in listings
        ],
        column_config={"Apply": st.column_config.LinkColumn(display_text="Open listing")},
        hide_index=True,
        use_container_width=True,
    )


if __name__ == "__main__":
    main()

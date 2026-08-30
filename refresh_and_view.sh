#!/usr/bin/env bash
# One command for a fresh look at the job market: scans Job Bank + Eluta for
# every configured title/location, backfills title/date/experience cleanup
# (same steps the scheduled cloud run does), then opens the dashboard.
#
#   ./refresh_and_view.sh
#
# The scan alone can take several minutes -- it's rate-limited to one
# request per second per site (steering: respect scraping etiquette) and
# now searches every target title across all your locations, not just one.
set -e

echo "Scanning Job Bank and Eluta for new listings -- this can take several minutes..."
python run_cycle.py

echo "Cleaning up titles/locations..."
python -m jobedge.backfill_titles

echo "Classifying experience level..."
python -m jobedge.backfill_experience

echo "Opening the dashboard..."
python3 -m streamlit run jobedge/dashboard.py

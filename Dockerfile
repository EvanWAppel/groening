FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App source.
COPY . .

# Bake the DuckDB warehouse into the image at build time. Railway's release
# phase runs in a throwaway container, so the build must happen here (fetches
# the PortlandMaps / Metro RLIS / EPA / NOAA / USGS sources, then materializes
# the dbt marts). The DB stays out of git and is rebuilt fresh on every deploy.
RUN python build_warehouse.py && dbt build --profiles-dir .

# Railway injects $PORT at runtime; default to 8501 for local runs. Exec form
# (via sh -c so $PORT still expands) so Streamlit receives SIGTERM directly.
EXPOSE 8501
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port ${PORT:-8501} --server.address 0.0.0.0"]

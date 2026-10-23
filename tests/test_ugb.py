"""TDD for the Metro Urban Growth Boundary fetch.

The original Metro DRC layer (services1 .../Urban_Growth_Boundary) was retired
around 2026-10-18 and now answers "Invalid URL", which broke every deploy. The
authoritative copy is published by the OregonMetro.RLIS ArcGIS Online account;
its area field is ``AREA`` (square feet), not the old ``AREA_``.
"""

import json

import pandas as pd
import pytest

import build_warehouse
import city_config as cfg

RLIS_UGB_URL = (
    "https://services2.arcgis.com/McQ0OlIABe29rJJy/arcgis/rest/services/"
    "Urban_Growth_Boundary_UGB/FeatureServer/0"
)


class TestUgbSource:
    def test_points_at_the_metro_rlis_layer(self):
        assert cfg.UGB_URL == RLIS_UGB_URL

    def test_catalog_cites_the_same_url(self):
        assert cfg.SOURCES["ugb"]["url"] == cfg.UGB_URL

    def test_catalog_keeps_the_rlis_license(self):
        assert "RLIS Open Database License" in cfg.SOURCES["ugb"]["license"]


class TestFetchUgb:
    @pytest.fixture
    def fake_features(self, monkeypatch, polygon_geom):
        def install(attrs: dict | None, geom: dict | None = polygon_geom):
            feats = [] if attrs is None else [(attrs, geom)]
            monkeypatch.setattr(
                build_warehouse, "fetch_features", lambda *a, **k: feats
            )

        return install

    def test_reads_area_from_the_rlis_area_field(self, fake_features, polygon_geom):
        fake_features({"FID": 1, "UGB": 1, "AREA": 11421078935.1})
        df = build_warehouse.fetch_ugb()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.loc[0, "area_sqft"] == pytest.approx(11421078935.1)
        assert json.loads(df.loc[0, "boundary_json"]) == polygon_geom["rings"][0]

    def test_no_feature_still_raises(self, fake_features):
        fake_features(None)
        with pytest.raises(ValueError, match="ugb: no feature returned"):
            build_warehouse.fetch_ugb()

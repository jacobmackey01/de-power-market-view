from de_power_market_view.smard import FILTERS, SmardClient


def test_filter_set_is_explicit_and_unique():
    assert set(FILTERS) == {
        "price_da",
        "load_actual",
        "wind_onshore_actual",
        "wind_offshore_actual",
        "solar_actual",
    }
    assert len(set(FILTERS.values())) == len(FILTERS)
    assert SmardClient().provenance() == []

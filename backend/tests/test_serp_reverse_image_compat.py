from serp_client import SerpClient


def test_reverse_image_search_wrapper_delegates_and_truncates():
    client = SerpClient.__new__(SerpClient)
    calls = {"count": 0}

    def fake_google_lens(image_url: str):
        calls["count"] += 1
        assert image_url == "https://example.com/image.jpg"
        return [{"id": i} for i in range(10)]

    client.reverse_image_search_google_lens_url = fake_google_lens  # type: ignore[attr-defined]

    results = client.reverse_image_search(
        "https://example.com/image.jpg",
        num_results=4,
    )

    assert calls["count"] == 1
    assert len(results) == 4
    assert results[0]["id"] == 0
    assert results[-1]["id"] == 3

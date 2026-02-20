from types import SimpleNamespace

from PIL import Image

from gemini_client import GeminiClient


class _FakeInlineData:
    def __init__(self, data: bytes):
        self.data = data


class _FakePart:
    def __init__(self, data: bytes):
        self.inline_data = _FakeInlineData(data)


class _FakeResponse:
    def __init__(self, data: bytes):
        self.parts = [_FakePart(data)]


class _FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return _FakeResponse(b"fake_png_bytes")


def test_generate_room_redesign_anchors_prompt_second_with_frame_lock(tmp_path):
    room_path = tmp_path / "room.png"
    inspiration_path = tmp_path / "inspiration.png"
    Image.new("RGB", (300, 200), color="white").save(room_path)
    Image.new("RGB", (200, 300), color="gray").save(inspiration_path)

    fake_models = _FakeModels()
    client = GeminiClient.__new__(GeminiClient)
    client.client = SimpleNamespace(models=fake_models)
    client._download_image = lambda image_url: Image.new("RGB", (64, 64), color="blue")

    generated_b64, model_used = client.generate_room_redesign(
        original_room_image_path=str(room_path),
        prompt="Base prompt body",
        product_images=[{"image_url": "https://example.com/prod.png", "title": "Sofa"}],
        inspiration_images=[str(inspiration_path)],
    )

    assert generated_b64
    assert model_used == fake_models.calls[0]["model"]

    contents = fake_models.calls[0]["contents"]
    assert len(contents) == 4
    assert isinstance(contents[0], Image.Image)
    assert isinstance(contents[1], str)
    assert isinstance(contents[2], Image.Image)
    assert isinstance(contents[3], Image.Image)

    final_prompt = contents[1]
    assert "NON-NEGOTIABLE FRAME LOCK" in final_prompt
    assert "Do NOT crop, zoom, recompose, rotate, or change perspective." in final_prompt
    assert "When counting image attachments only" in final_prompt
    assert "Technical Requirement: Preserve the exact input image aspect ratio." in final_prompt

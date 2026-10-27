import json

from django.test import Client, TestCase

from .imaging import apply_kernel
from .models import Drawing, MagicLens

FLAT = [[100] * 8 for _ in range(8)]
BLUR = [[1] * 3] * 3


class ApplyKernelTests(TestCase):
    def test_blur_and_sharpen_keep_flat_image(self):
        self.assertEqual(apply_kernel(FLAT, BLUR, 9), FLAT)
        self.assertEqual(apply_kernel(FLAT, [[0, -1, 0], [-1, 5, -1], [0, -1, 0]], 1), FLAT)

    def test_edge_kernel_gives_black_on_flat_image(self):
        out = apply_kernel(FLAT, [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]], 1)
        self.assertEqual(out, [[0] * 8 for _ in range(8)])


class ApplyLensTests(TestCase):
    def setUp(self):
        self.lens = MagicLens.objects.create(name="Flou", slug="flou", kernel=BLUR, divisor=9)
        self.drawing = Drawing.objects.create(title="Plat", pixels=FLAT)

    def post(self, body, client=None):
        data = body if isinstance(body, str) else json.dumps(body)
        return (client or self.client).post("/api/apply/", data, content_type="application/json")

    def test_get_endpoints(self):
        self.assertEqual(self.client.get(f"/api/lens/{self.lens.pk}/").json()["divisor"], 9)
        self.assertEqual(self.client.get(f"/api/drawing/{self.drawing.pk}/").json()["pixels"], FLAT)
        self.assertEqual(self.client.get("/api/lens/999/").status_code, 404)

    def test_with_drawing_id(self):
        r = self.post({"lens_id": self.lens.pk, "drawing_id": self.drawing.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["pixels"], FLAT)

    def test_with_student_pixels(self):
        self.assertTrue(self.post({"lens_id": self.lens.pk, "pixels": FLAT}).json()["success"])

    def test_bad_inputs_give_json_errors(self):
        for body in ("pas du json", {}, {"lens_id": "x"}, {"lens_id": self.lens.pk},
                     {"lens_id": self.lens.pk, "pixels": [[1, 2]]},
                     {"lens_id": self.lens.pk, "pixels": [[999] * 8] * 8},
                     {"lens_id": 999, "drawing_id": 1},
                     {"lens_id": self.lens.pk, "drawing_id": 999}):
            r = self.post(body)
            self.assertIn(r.status_code, (400, 404), body)
            self.assertFalse(r.json()["success"])

    def test_csrf_is_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        r = self.post({"lens_id": self.lens.pk, "drawing_id": self.drawing.pk}, strict)
        self.assertEqual(r.status_code, 403)
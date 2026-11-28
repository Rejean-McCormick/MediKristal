import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

from scripts import download_medical_sources as downloader


class Response(io.BytesIO):
    def __init__(self, content, size=None):
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content) if size is None else size)}


class DownloadMedicalSourcesTests(unittest.TestCase):
    def test_default_destination_is_sibling_of_repository(self):
        self.assertEqual(downloader.ROOT.parent / "MediKristal-Donnees", downloader.DEFAULT_DESTINATION)

    def test_download_publishes_matching_file_and_receipt_once(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("test.txt", "synthetic")
        payload = stream.getvalue()
        artifact = downloader.Artifact(
            "test.zip", "https://example.test/source.zip", "https://example.test",
            checksum=("md5", hashlib.md5(payload, usedforsecurity=False).hexdigest()),
        )
        with tempfile.TemporaryDirectory() as temp, patch.object(
            downloader, "request", side_effect=lambda *args, **kwargs: Response(payload)
        ):
            root = Path(temp)
            result = downloader.download(root, "test", artifact, request_url="https://example.test/?apiKey=secret")
            self.assertEqual(result, downloader.download(root, "test", artifact))
            self.assertEqual(result.read_bytes(), payload)
            manifest = (result.parent / "provenance.json").read_text(encoding="utf-8")
            self.assertEqual(json.loads(manifest)["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertNotIn("secret", manifest)
            self.assertEqual(len(list(root.rglob("provenance.json"))), 1)

    def test_incomplete_or_wrong_content_is_not_published(self):
        artifact = downloader.Artifact("test.zip", "https://example.test/test.zip", "https://example.test")
        for size in (200, None):
            with tempfile.TemporaryDirectory() as temp, patch.object(
                downloader, "request", return_value=Response(b"<html>Login</html>", size)
            ):
                root = Path(temp)
                with self.assertRaises((downloader.DownloadError, zipfile.BadZipFile)):
                    downloader.download(root, "test", artifact)
                self.assertEqual(list(root.rglob("*.zip")), [])
                self.assertEqual(list(root.rglob(".telechargement-*")), [])

    def test_syndication_selects_latest_ccdd_csv_with_publisher_checksum(self):
        older = "1" * 64
        newer = "2" * 64
        payload = f"""
        <feed xmlns="http://www.w3.org/2005/Atom"
              xmlns:ncts="http://ns.electronichealth.net.au/ncts/syndication/asf/extensions/1.0.0">
          <entry><title>Ancienne version déjà republiée</title><link type="application/zip"
            href="{downloader.INFOWAY}/ccdd_csv_20260115.zip" ncts:sha256Hash="{older}"/></entry>
          <entry><title>Version récente</title><link type="application/zip"
            href="{downloader.INFOWAY}/ccdd_csv_20260215.zip" ncts:sha256Hash="{newer}" length="123"/></entry>
          <entry><title>Version Excel</title><link type="application/zip"
            href="{downloader.INFOWAY}/ccdd_excel_20260315.zip"/></entry>
        </feed>""".encode("cp1252")
        artifact = downloader.infoway_artifact("ccdd", payload)
        self.assertTrue(artifact.url.endswith("ccdd_csv_20260215.zip"))
        self.assertEqual((artifact.checksum, artifact.size), (("sha256", newer), 123))

    def test_redirect_keeps_authorization_same_origin_and_strips_it_cross_origin(self):
        request = Request("https://example.test/start", headers={"Authorization": "Bearer secret"})
        handler = downloader.HTTPSRedirects()
        same_origin = handler.redirect_request(request, None, 302, "Found", {}, "https://example.test/file")
        self.assertTrue(same_origin.has_header("Authorization"))
        cross_origin = handler.redirect_request(request, None, 302, "Found", {}, "https://other.test/file")
        self.assertFalse(cross_origin.has_header("Authorization"))
        with self.assertRaises(downloader.DownloadError):
            handler.redirect_request(request, None, 302, "Found", {}, "http://example.test/file")

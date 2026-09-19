import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


CRAWLER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CRAWLER_DIR))

from twitter_Crawler_2 import DEFAULT_CONFIG, build_media_page_tasks, is_media_page_url, media_page_url
from download_method import image_content_as_png, media_filename, normalize_proxy_url, proxies_from_windows_proxy_server
from manga_downloader import cleanup_png_image_duplicates, is_timeline_response_url, normalize_photo_url


class MediaPageRouteTests(unittest.TestCase):
    def test_combined_types_scan_photo_and_video_views(self):
        self.assertEqual(
            build_media_page_tasks("https://x.com/example/media", "1234"),
            [
                ("图片", "https://x.com/example/media?filter=photo", "1"),
                ("视频/GIF/音频", "https://x.com/example/media", "234"),
            ],
        )

    def test_existing_filter_is_replaced_without_losing_other_query_values(self):
        target = "https://x.com/example/media?foo=1&filter=photo"
        self.assertEqual(media_page_url(target), "https://x.com/example/media?foo=1")
        self.assertEqual(media_page_url(target, "photo"), "https://x.com/example/media?foo=1&filter=photo")

    def test_photo_query_is_still_a_media_route(self):
        self.assertTrue(is_media_page_url("https://x.com/example/media?filter=photo"))

    def test_current_x_photo_and_video_timelines_are_collected(self):
        self.assertTrue(
            is_timeline_response_url(
                "https://x.com/i/api/graphql/query-id/UserPhotoTimeline",
                is_media=True,
            )
        )
        self.assertTrue(
            is_timeline_response_url(
                "https://x.com/i/api/graphql/query-id/UserVideoTimeline",
                is_media=True,
            )
        )
        self.assertTrue(
            is_timeline_response_url(
                "https://x.com/i/api/graphql/query-id/UserMedia",
                is_media=True,
            )
        )
        self.assertFalse(
            is_timeline_response_url(
                "https://x.com/i/api/graphql/query-id/UserByScreenName",
                is_media=True,
            )
        )

    def test_windows_proxy_syntax_converts_to_requests_mapping(self):
        self.assertEqual(
            proxies_from_windows_proxy_server("http=127.0.0.1:7890;https=127.0.0.1:7891"),
            {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7891"},
        )
        self.assertEqual(
            proxies_from_windows_proxy_server("127.0.0.1:7890"),
            {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
        )
        self.assertEqual(normalize_proxy_url("https://example.test:443"), "https://example.test:443")

    def test_smaller_gif_defaults_preserve_source_mp4(self):
        self.assertEqual(DEFAULT_CONFIG["gif_fps"], 8)
        self.assertEqual(DEFAULT_CONFIG["gif_width"], 720)
        self.assertTrue(DEFAULT_CONFIG["keep_gif_mp4"])

    def test_photo_urls_normalize_to_png_for_deduplication(self):
        self.assertEqual(
            normalize_photo_url("https://pbs.twimg.com/media/example?format=jpg&name=large"),
            "https://pbs.twimg.com/media/example?format=png&name=large",
        )

    def test_downloaded_images_are_encoded_as_png(self):
        source = BytesIO()
        Image.new("RGB", (2, 2), "red").save(source, format="JPEG")

        png = image_content_as_png(source.getvalue())

        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(
            media_filename("https://pbs.twimg.com/media/example?format=jpg", ".png", force_ext=True),
            "example.png",
        )

    def test_cleanup_removes_only_crawler_jpegs_with_a_png_sibling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            png = folder / "20260101_120000_1234567890123456789_img01.png"
            duplicate_jpg = folder / "1234567890123456789_img01.jpg"
            jpg_without_png = folder / "1234567890123456790_img01.jpg"
            unrelated_jpg = folder / "manual-photo.jpg"
            png.write_bytes(b"png")
            duplicate_jpg.write_bytes(b"jpg")
            jpg_without_png.write_bytes(b"keep")
            unrelated_jpg.write_bytes(b"keep")

            result = cleanup_png_image_duplicates(folder)

            self.assertEqual(result["files"], 1)
            self.assertFalse(duplicate_jpg.exists())
            self.assertTrue(png.exists())
            self.assertTrue(jpg_without_png.exists())
            self.assertTrue(unrelated_jpg.exists())


if __name__ == "__main__":
    unittest.main()

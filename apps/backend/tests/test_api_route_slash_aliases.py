import unittest

from app.api.routes import admin_chats
from app.api.routes import blog_posts
from app.api.routes import contact_requests
from app.api.routes import generation_jobs
from app.api.routes import projects
from app.api.routes import site_settings
from app.api.routes import stylist_runtime_settings
from app.api.routes import uploads


def _has_route(router, path: str, method: str) -> bool:
    normalized_method = method.upper()
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        if getattr(route, "path", None) == path and normalized_method in methods:
            return True
    return False


class ApiRouteSlashAliasesTests(unittest.TestCase):
    def test_collection_routes_accept_trailing_and_non_trailing_slash(self) -> None:
        expectations = [
            (stylist_runtime_settings.router, "/stylist-runtime-settings", "GET"),
            (stylist_runtime_settings.router, "/stylist-runtime-settings/", "GET"),
            (stylist_runtime_settings.router, "/stylist-runtime-settings", "PUT"),
            (stylist_runtime_settings.router, "/stylist-runtime-settings/", "PUT"),
            (site_settings.router, "/site-settings", "GET"),
            (site_settings.router, "/site-settings/", "GET"),
            (site_settings.router, "/site-settings", "PUT"),
            (site_settings.router, "/site-settings/", "PUT"),
            (generation_jobs.router, "/generation-jobs", "GET"),
            (generation_jobs.router, "/generation-jobs/", "GET"),
            (generation_jobs.router, "/generation-jobs", "POST"),
            (generation_jobs.router, "/generation-jobs/", "POST"),
            (projects.router, "/projects", "GET"),
            (projects.router, "/projects/", "GET"),
            (projects.router, "/projects", "POST"),
            (projects.router, "/projects/", "POST"),
            (blog_posts.router, "/blog-posts", "GET"),
            (blog_posts.router, "/blog-posts/", "GET"),
            (blog_posts.router, "/blog-posts", "POST"),
            (blog_posts.router, "/blog-posts/", "POST"),
            (contact_requests.router, "/contact-requests", "GET"),
            (contact_requests.router, "/contact-requests/", "GET"),
            (contact_requests.router, "/contact-requests", "POST"),
            (contact_requests.router, "/contact-requests/", "POST"),
            (uploads.router, "/uploads", "POST"),
            (uploads.router, "/uploads/", "POST"),
            (admin_chats.router, "/admin/chats", "GET"),
            (admin_chats.router, "/admin/chats/", "GET"),
        ]

        for router, path, method in expectations:
            with self.subTest(path=path, method=method):
                self.assertTrue(_has_route(router, path, method))


if __name__ == "__main__":
    unittest.main()

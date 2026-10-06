# SPDX-License-Identifier: AGPL-3.0-or-later
import frappe

from insights.insights.doctype.insights_data_source.sources.frappe_db import SiteDB
from insights.tests.base import InsightsIntegrationTestCase

SITE_DB = "Site DB"
SSL_URL_KEYS = ("ssl", "ssl_ca", "ssl_cert", "ssl_key", "ssl_check_hostname", "ssl_verify_cert")


class TestSiteDBConnection(InsightsIntegrationTestCase):
    """The site's own database is reached exactly as Frappe reaches it."""

    def tearDown(self):
        for key in ("db_ssl_ca", "db_ssl_cert", "db_ssl_key", "db_ssl_check_hostname"):
            frappe.local.conf.pop(key, None)
        super().tearDown()

    def test_connects_without_tls_when_the_site_has_no_db_ssl_ca(self):
        site_db = SiteDB(SITE_DB)
        self.assertFalse(set(site_db.engine.url.query) & set(SSL_URL_KEYS), site_db.engine.url.query)
        # A live round trip: a server that offers TLS with a self-signed certificate (MariaDB
        # 11.4+ by default) used to fail here with CERTIFICATE_VERIFY_FAILED.
        self.assertTrue(site_db.test_connection(log_errors=False))

    def test_follows_the_sites_db_ssl_settings(self):
        frappe.local.conf.db_ssl_ca = "/etc/mysql/ssl/ca.pem"
        frappe.local.conf.db_ssl_cert = "/etc/mysql/ssl/client-cert.pem"
        frappe.local.conf.db_ssl_key = "/etc/mysql/ssl/client-key.pem"
        frappe.local.conf.db_ssl_check_hostname = True
        engine = SiteDB(SITE_DB).engine
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        self.assertEqual(
            kwargs["ssl"],
            {
                "ca": "/etc/mysql/ssl/ca.pem",
                "cert": "/etc/mysql/ssl/client-cert.pem",
                "key": "/etc/mysql/ssl/client-key.pem",
                "check_hostname": True,
            },
        )
        self.assertNotIn("ssl_verify_cert", kwargs)

    def test_client_certificate_only_with_both_cert_and_key(self):
        frappe.local.conf.db_ssl_ca = "/etc/mysql/ssl/ca.pem"
        frappe.local.conf.db_ssl_cert = "/etc/mysql/ssl/client-cert.pem"
        engine = SiteDB(SITE_DB).engine
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        self.assertEqual(kwargs["ssl"], {"ca": "/etc/mysql/ssl/ca.pem", "check_hostname": False})

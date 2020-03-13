# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from memo.migration.testing import MEMO_MIGRATION_INTEGRATION_TESTING  # noqa

import unittest


class TestSetup(unittest.TestCase):
    """Test that memo.migration is properly installed."""

    layer = MEMO_MIGRATION_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if memo.migration is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'memo.migration'))

    def test_browserlayer(self):
        """Test that IMemoMigrationLayer is registered."""
        from memo.migration.interfaces import (
            IMemoMigrationLayer)
        from plone.browserlayer import utils
        self.assertIn(
            IMemoMigrationLayer,
            utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = MEMO_MIGRATION_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.installer.uninstallProducts(['memo.migration'])
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if memo.migration is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'memo.migration'))

    def test_browserlayer_removed(self):
        """Test that IMemoMigrationLayer is removed."""
        from memo.migration.interfaces import \
            IMemoMigrationLayer
        from plone.browserlayer import utils
        self.assertNotIn(
            IMemoMigrationLayer,
            utils.registered_layers())

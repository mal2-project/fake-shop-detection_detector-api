# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.black_list_entry import BlackListEntry  # noqa: E501
from swagger_server.models.grey_list_entry import GreyListEntry  # noqa: E501
from swagger_server.models.ignore_list_entry import IgnoreListEntry  # noqa: E501
from swagger_server.models.inline_response400 import InlineResponse400  # noqa: E501
from swagger_server.models.site import Site  # noqa: E501
from swagger_server.models.site_analysis_result import SiteAnalysisResult  # noqa: E501
from swagger_server.models.white_list_entry import WhiteListEntry  # noqa: E501
from swagger_server.test import BaseTestCase


class TestPluginController(BaseTestCase):
    """PluginController integration test stubs"""

    def test_analyze_post(self):
        """Test case for analyze_post

        request Fake-Score analysis result of a given site
        """
        body = Site()
        response = self.client.open(
            '/malzwei/ecommerce/1.1/analyze',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_blacklist_get(self):
        """Test case for blacklist_get

        returns all blacklisted shops
        """
        query_string = [('limit', 56),
                        ('offset', 56),
                        ('all', true),
                        ('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/blacklist',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_blacklist_site_id_get(self):
        """Test case for blacklist_site_id_get

        returns information on a specific blacklisted site
        """
        query_string = [('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/blacklist/{site_id}'.format(site_id='site_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_greylist_get(self):
        """Test case for greylist_get

        returns all greylisted shops
        """
        query_string = [('limit', 56),
                        ('offset', 56),
                        ('all', true),
                        ('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/greylist',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_greylist_site_id_get(self):
        """Test case for greylist_site_id_get

        returns information on a specific greylisted site
        """
        query_string = [('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/greylist/{site_id}'.format(site_id='site_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_ignorelist_get(self):
        """Test case for ignorelist_get

        returns all ignorelisted shops
        """
        query_string = [('limit', 56),
                        ('offset', 56),
                        ('all', true),
                        ('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/ignorelist',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_ignorelist_site_id_get(self):
        """Test case for ignorelist_site_id_get

        returns information on a specific ignorelisted site
        """
        query_string = [('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/ignorelist/{site_id}'.format(site_id='site_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_whitelist_get(self):
        """Test case for whitelist_get

        returns all whitelisted shops
        """
        query_string = [('limit', 56),
                        ('offset', 56),
                        ('all', true),
                        ('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/whitelist',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_whitelist_site_id_get(self):
        """Test case for whitelist_site_id_get

        returns information on a specific whitelisted site
        """
        query_string = [('client_id', 'client_id_example')]
        response = self.client.open(
            '/malzwei/ecommerce/1.1/whitelist/{site_id}'.format(site_id='site_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()

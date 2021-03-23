# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.inline_response400 import InlineResponse400  # noqa: E501
from swagger_server.models.site import Site  # noqa: E501
from swagger_server.models.site_analysis_result import SiteAnalysisResult  # noqa: E501
from swagger_server.test import BaseTestCase


class TestExpertController(BaseTestCase):
    """ExpertController integration test stubs"""

    def test_reanalyze_post(self):
        """Test case for reanalyze_post

        request Fake-Score re-analysis of a given site
        """
        body = Site()
        response = self.client.open(
            '/malzwei/ecommerce/1.1/reanalyze',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()

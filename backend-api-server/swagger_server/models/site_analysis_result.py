# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class SiteAnalysisResult(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, site_id: str=None, site_url: str=None, analyzed_date_time: datetime=None, processor: str=None, risk_score: str=None):  # noqa: E501
        """SiteAnalysisResult - a model defined in Swagger

        :param site_id: The site_id of this SiteAnalysisResult.  # noqa: E501
        :type site_id: str
        :param site_url: The site_url of this SiteAnalysisResult.  # noqa: E501
        :type site_url: str
        :param analyzed_date_time: The analyzed_date_time of this SiteAnalysisResult.  # noqa: E501
        :type analyzed_date_time: datetime
        :param processor: The processor of this SiteAnalysisResult.  # noqa: E501
        :type processor: str
        :param risk_score: The risk_score of this SiteAnalysisResult.  # noqa: E501
        :type risk_score: str
        """
        self.swagger_types = {
            'site_id': str,
            'site_url': str,
            'analyzed_date_time': datetime,
            'processor': str,
            'risk_score': str
        }

        self.attribute_map = {
            'site_id': 'site_id',
            'site_url': 'site_url',
            'analyzed_date_time': 'analyzed_date_time',
            'processor': 'processor',
            'risk_score': 'risk_score'
        }
        self._site_id = site_id
        self._site_url = site_url
        self._analyzed_date_time = analyzed_date_time
        self._processor = processor
        self._risk_score = risk_score

    @classmethod
    def from_dict(cls, dikt) -> 'SiteAnalysisResult':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Site-Analysis-Result of this SiteAnalysisResult.  # noqa: E501
        :rtype: SiteAnalysisResult
        """
        return util.deserialize_model(dikt, cls)

    @property
    def site_id(self) -> str:
        """Gets the site_id of this SiteAnalysisResult.


        :return: The site_id of this SiteAnalysisResult.
        :rtype: str
        """
        return self._site_id

    @site_id.setter
    def site_id(self, site_id: str):
        """Sets the site_id of this SiteAnalysisResult.


        :param site_id: The site_id of this SiteAnalysisResult.
        :type site_id: str
        """

        self._site_id = site_id

    @property
    def site_url(self) -> str:
        """Gets the site_url of this SiteAnalysisResult.


        :return: The site_url of this SiteAnalysisResult.
        :rtype: str
        """
        return self._site_url

    @site_url.setter
    def site_url(self, site_url: str):
        """Sets the site_url of this SiteAnalysisResult.


        :param site_url: The site_url of this SiteAnalysisResult.
        :type site_url: str
        """

        self._site_url = site_url

    @property
    def analyzed_date_time(self) -> datetime:
        """Gets the analyzed_date_time of this SiteAnalysisResult.


        :return: The analyzed_date_time of this SiteAnalysisResult.
        :rtype: datetime
        """
        return self._analyzed_date_time

    @analyzed_date_time.setter
    def analyzed_date_time(self, analyzed_date_time: datetime):
        """Sets the analyzed_date_time of this SiteAnalysisResult.


        :param analyzed_date_time: The analyzed_date_time of this SiteAnalysisResult.
        :type analyzed_date_time: datetime
        """

        self._analyzed_date_time = analyzed_date_time

    @property
    def processor(self) -> str:
        """Gets the processor of this SiteAnalysisResult.


        :return: The processor of this SiteAnalysisResult.
        :rtype: str
        """
        return self._processor

    @processor.setter
    def processor(self, processor: str):
        """Sets the processor of this SiteAnalysisResult.


        :param processor: The processor of this SiteAnalysisResult.
        :type processor: str
        """
        allowed_values = ["whitelist", "blacklist", "ignorelist", "greylist", "mal2_ai"]  # noqa: E501
        if processor not in allowed_values:
            raise ValueError(
                "Invalid value for `processor` ({0}), must be one of {1}"
                .format(processor, allowed_values)
            )

        self._processor = processor

    @property
    def risk_score(self) -> str:
        """Gets the risk_score of this SiteAnalysisResult.


        :return: The risk_score of this SiteAnalysisResult.
        :rtype: str
        """
        return self._risk_score

    @risk_score.setter
    def risk_score(self, risk_score: str):
        """Sets the risk_score of this SiteAnalysisResult.


        :param risk_score: The risk_score of this SiteAnalysisResult.
        :type risk_score: str
        """
        allowed_values = ["very low", "low", "below average", "above average", "high", "very high", "unknown"]  # noqa: E501
        if risk_score not in allowed_values:
            raise ValueError(
                "Invalid value for `risk_score` ({0}), must be one of {1}"
                .format(risk_score, allowed_values)
            )

        self._risk_score = risk_score

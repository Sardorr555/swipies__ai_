"""
Thanks to https://github.com/onyx-dot-app/onyx

Content of this directory is under the "MIT Expat" license as defined below.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Any

from common.constants import FileSource

try:
    from .airtable_connector import AirtableConnector
except (ImportError, Exception):
    AirtableConnector = None
try:
    from .asana_connector import AsanaConnector
except (ImportError, Exception):
    AsanaConnector = None
try:
    from .azure_blob_connector import AzureBlobConnector
except (ImportError, Exception):
    AzureBlobConnector = None
try:
    from .bigquery_connector import BigQueryConnector
except (ImportError, Exception):
    BigQueryConnector = None
try:
    from .azure_devops.connector import AzureDevOpsConnector
except (ImportError, Exception):
    AzureDevOpsConnector = None
try:
    from .bitbucket.connector import BitbucketConnector
except (ImportError, Exception):
    BitbucketConnector = None
try:
    from .blob_connector import BlobStorageConnector
except (ImportError, Exception):
    BlobStorageConnector = None
try:
    from .box_connector import BoxConnector
except (ImportError, Exception):
    BoxConnector = None
try:
    from .confluence_connector import ConfluenceConnector
except (ImportError, Exception):
    ConfluenceConnector = None
from .config import BlobType, DocumentSource
try:
    from .dingtalk_ai_table_connector import DingTalkAITableConnector
except (ImportError, Exception):
    DingTalkAITableConnector = None
try:
    from .discord_connector import DiscordConnector
except (ImportError, Exception):
    DiscordConnector = None
try:
    from .dropbox_connector import DropboxConnector
except (ImportError, Exception):
    DropboxConnector = None
from .exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
    CredentialExpiredError,
    InsufficientPermissionsError,
    UnexpectedValidationError,
)
try:
    from .github.connector import GithubConnector
except (ImportError, Exception):
    GithubConnector = None
try:
    from .gitlab_connector import GitlabConnector
except (ImportError, Exception):
    GitlabConnector = None
try:
    from .gmail_connector import GmailConnector
except (ImportError, Exception):
    GmailConnector = None
try:
    from .google_drive.connector import GoogleDriveConnector
except (ImportError, Exception):
    GoogleDriveConnector = None
try:
    from .imap_connector import ImapConnector
except (ImportError, Exception):
    ImapConnector = None
try:
    from .jira.connector import JiraConnector
except (ImportError, Exception):
    JiraConnector = None
from .models import BasicExpertInfo, Document, ImageSection, TextSection
try:
    from .moodle_connector import MoodleConnector
except (ImportError, Exception):
    MoodleConnector = None
try:
    from .notion_connector import NotionConnector
except (ImportError, Exception):
    NotionConnector = None
try:
    from .onedrive_connector import OneDriveConnector
except (ImportError, Exception):
    OneDriveConnector = None
try:
    from .outlook_connector import OutlookConnector
except (ImportError, Exception):
    OutlookConnector = None
try:
    from .rdbms_connector import RDBMSConnector
except (ImportError, Exception):
    RDBMSConnector = None
try:
    from .rest_api_connector import RestAPIConnector
except (ImportError, Exception):
    RestAPIConnector = None
try:
    from .rss_connector import RSSConnector
except (ImportError, Exception):
    RSSConnector = None
try:
    from .salesforce_connector import SalesforceConnector
except (ImportError, Exception):
    SalesforceConnector = None
try:
    from .seafile_connector import SeaFileConnector
except (ImportError, Exception):
    SeaFileConnector = None
try:
    from .sharepoint_connector import SharePointConnector
except (ImportError, Exception):
    SharePointConnector = None
try:
    from .sitemap_connector import SitemapConnector
except (ImportError, Exception):
    SitemapConnector = None
try:
    from .slack_connector import SlackConnector
except (ImportError, Exception):
    SlackConnector = None
try:
    from .teams_connector import TeamsConnector
except (ImportError, Exception):
    TeamsConnector = None
try:
    from .webdav_connector import WebDAVConnector
except (ImportError, Exception):
    WebDAVConnector = None
try:
    from .xquik_connector import XquikConnector
except (ImportError, Exception):
    XquikConnector = None
try:
    from .zendesk_connector import ZendeskConnector
except (ImportError, Exception):
    ZendeskConnector = None
from .bitrix24_connector import Bitrix24Connector
from .amocrm_connector import AmoCRMConnector
from .hubspot_connector import HubSpotConnector
from .onec_connector import OneCConnector

_RAW_CONNECTOR_BY_SOURCE: dict[str, type | None] = {
    FileSource.S3: BlobStorageConnector,
    FileSource.R2: BlobStorageConnector,
    FileSource.OCI_STORAGE: BlobStorageConnector,
    FileSource.GOOGLE_CLOUD_STORAGE: BlobStorageConnector,
    FileSource.RSS: RSSConnector,
    FileSource.CONFLUENCE: ConfluenceConnector,
    FileSource.NOTION: NotionConnector,
    FileSource.DISCORD: DiscordConnector,
    FileSource.GMAIL: GmailConnector,
    FileSource.DROPBOX: DropboxConnector,
    FileSource.GOOGLE_DRIVE: GoogleDriveConnector,
    FileSource.JIRA: JiraConnector,
    FileSource.SHAREPOINT: SharePointConnector,
    FileSource.SITEMAP: SitemapConnector,
    FileSource.SLACK: SlackConnector,
    FileSource.TEAMS: TeamsConnector,
    FileSource.WEBDAV: WebDAVConnector,
    FileSource.MOODLE: MoodleConnector,
    FileSource.BOX: BoxConnector,
    FileSource.AIRTABLE: AirtableConnector,
    FileSource.ASANA: AsanaConnector,
    FileSource.GITHUB: GithubConnector,
    FileSource.IMAP: ImapConnector,
    FileSource.ZENDESK: ZendeskConnector,
    FileSource.GITLAB: GitlabConnector,
    FileSource.BITBUCKET: BitbucketConnector,
    FileSource.AZURE_DEVOPS: AzureDevOpsConnector,
    FileSource.SEAFILE: SeaFileConnector,
    FileSource.DINGTALK_AI_TABLE: DingTalkAITableConnector,
    FileSource.MYSQL: RDBMSConnector,
    FileSource.POSTGRESQL: RDBMSConnector,
    FileSource.REST_API: RestAPIConnector,
    FileSource.XQUIK: XquikConnector,
    FileSource.BIGQUERY: BigQueryConnector,
    FileSource.ONEDRIVE: OneDriveConnector,
    FileSource.OUTLOOK: OutlookConnector,
    FileSource.SALESFORCE: SalesforceConnector,
    FileSource.AZURE_BLOB: AzureBlobConnector,
    FileSource.BITRIX24: Bitrix24Connector,
    FileSource.AMOCRM: AmoCRMConnector,
    FileSource.KOMMO: AmoCRMConnector,
    FileSource.HUBSPOT: HubSpotConnector,
    FileSource.ONE_C: OneCConnector,
}

CONNECTOR_BY_SOURCE: dict[str, type] = {
    source: connector_cls
    for source, connector_cls in _RAW_CONNECTOR_BY_SOURCE.items()
    if connector_cls is not None
}



def build_connector_for_source(source: str, config: dict[str, Any]) -> Any:
    connector_cls = CONNECTOR_BY_SOURCE.get(source)
    if connector_cls is None:
        raise ConnectorValidationError(f"Unsupported data source type: {source}")
    if connector_cls is BlobStorageConnector:
        return connector_cls.build_connector(config, bucket_type=config.get("bucket_type") or source)
    if connector_cls is RDBMSConnector:
        return connector_cls.build_connector(config, db_type=source)
    return connector_cls.build_connector(config)


__all__ = [
    "CONNECTOR_BY_SOURCE",
    "AirtableConnector",
    "AmoCRMConnector",
    "AsanaConnector",
    "AzureBlobConnector",
    "AzureDevOpsConnector",
    "BasicExpertInfo",
    "BigQueryConnector",
    "BitbucketConnector",
    "Bitrix24Connector",
    "BlobStorageConnector",
    "BlobType",
    "BoxConnector",
    "ConfluenceConnector",
    "ConnectorMissingCredentialError",
    "ConnectorValidationError",
    "CredentialExpiredError",
    "DingTalkAITableConnector",
    "DiscordConnector",
    "Document",
    "DocumentSource",
    "DropboxConnector",
    "GithubConnector",
    "GitlabConnector",
    "GmailConnector",
    "GoogleDriveConnector",
    "HubSpotConnector",
    "ImageSection",
    "ImapConnector",
    "InsufficientPermissionsError",
    "JiraConnector",
    "MoodleConnector",
    "NotionConnector",
    "OneCConnector",
    "OneDriveConnector",
    "OutlookConnector",
    "RDBMSConnector",
    "RSSConnector",
    "RestAPIConnector",
    "SalesforceConnector",
    "SeaFileConnector",
    "SharePointConnector",
    "SitemapConnector",
    "SlackConnector",
    "TeamsConnector",
    "TextSection",
    "UnexpectedValidationError",
    "WebDAVConnector",
    "XquikConnector",
    "ZendeskConnector",
    "build_connector_for_source",
]

import pytest
import asyncio
from app.agents.repository_context import _find_related_files, _extract_import_dependencies
from app.services.gitlab import GitLabService

class MockGitLabService(GitLabService):
    def __init__(self):
        self.target_app_path = ""
        self.project_encoded = ""
        self.base_url = ""
        self.headers = {}
        self.target_branch = "main"

    async def get_repository_tree(self, path="", ref=None, recursive=False):
        if path == "currency":
            return [
                {"type": "blob", "path": "currency/__init__.py"},
                {"type": "blob", "path": "currency/converter.py"},
                {"type": "blob", "path": "currency/utils.py"}
            ]
        return []

    async def get_file_content(self, file_path, ref=None):
        if file_path == "currency/converter.py":
            return "import os\nfrom datetime import datetime\nimport json\nimport external_lib\n"
        if file_path == "currency/utils.py":
            return "import re\nfrom itertools import chain\n"
        return ""

@pytest.mark.asyncio
async def test_find_related_files():
    gitlab = MockGitLabService()
    related = await _find_related_files(gitlab, "currency/converter.py", 1)
    assert "currency/__init__.py" in related
    assert "currency/utils.py" in related
    assert "currency/converter.py" not in related

@pytest.mark.asyncio
async def test_extract_import_dependencies():
    gitlab = MockGitLabService()
    deps = await _extract_import_dependencies(gitlab, "currency/converter.py", ["currency/utils.py"], 1)
    # os, datetime, json, re, itertools are stdlib and should be filtered
    assert "external_lib" in deps
    assert "os" not in deps
    assert "json" not in deps
    assert "re" not in deps

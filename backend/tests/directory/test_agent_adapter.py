from bandit.directory.domain.models import ExtractedRecord
from bandit.directory.infrastructure.gemini_agent import execute_tool, record_from_arguments
from bandit.directory.infrastructure.pdf_text import read_pdf_text


class RecordingTools:
    def __init__(self):
        self.calls = []

    async def open_listing_page(self, page):
        self.calls.append(("page", page))
        return "página"

    async def read_flyer(self, url):
        self.calls.append(("flyer", url))
        return "volante"

    def submit_record(self, record):
        self.calls.append(("record", record))
        return "ok"

    def finish(self):
        self.calls.append(("finish",))
        return "fin"


def test_builds_a_record_from_model_arguments():
    record = record_from_arguments(
        {"name": "Ana", "alias": "", "hotline_phones": ["300", "301"], "crime": "Hurto"}
    )

    assert record == ExtractedRecord(
        "Ana", None, "Hurto", None, None, None, ("300", "301"), None, None
    )


async def test_dispatches_each_allowed_tool():
    tools = RecordingTools()

    await execute_tool(tools, "open_listing_page", {"page": 2.0})
    await execute_tool(tools, "read_flyer", {"url": "u"})
    await execute_tool(tools, "submit_record", {"name": "Ana"})
    await execute_tool(tools, "finish", {})

    assert [call[0] for call in tools.calls] == ["page", "flyer", "record", "finish"]
    assert tools.calls[0] == ("page", 2)


async def test_unknown_tools_do_nothing():
    tools = RecordingTools()

    assert await execute_tool(tools, "delete_everything", {}) == "Herramienta desconocida."
    assert tools.calls == []


def test_unreadable_pdf_returns_empty_text():
    assert read_pdf_text(b"no es un pdf") == ""

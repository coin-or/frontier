"""Wire-size guards: tool results serve as compact JSON, sent once.

Two SDK behaviors inflated every response: dict results were pretty-printed
(indent=2, +35-65%) and dict-annotated tools also shipped a structuredContent
duplicate. A 41KB tradeoffs payload served at ~68KB and crossed the client's
inline cap — agents got a persisted-output file instead of readable JSON.
"""
import mcp_server.server as server


def test_tool_results_serialize_compact():
    from mcp.server.fastmcp.utilities import func_metadata as fm

    out = fm._convert_to_content({"a": [1, 2], "b": {"c": 1.5}})
    assert out[0].text == '{"a":[1,2],"b":{"c":1.5}}'


def test_dict_tools_skip_structured_content():
    tools = server.mcp._tool_manager.list_tools()
    by_name = {t.name: t for t in tools}
    for name in ("model", "solve", "explore"):
        assert by_name[name].fn_metadata.output_model is None, (
            f"{name} would double-send as structuredContent")

"""Verify the installed ibflex hits the correct Flex Web Service URL
and can fetch the reference code for the configured token/query.
"""
import re
from pathlib import Path

import ibflex
import ibflex.client as ibclient


CONFIG = Path.home() / ".compare_my_stocks" / "myconfig.yaml"


def _load_flex_creds():
    text = CONFIG.read_text()
    tok = re.search(r"FlexToken:\s*(\S+)", text)
    qry = re.search(r"FlexQuery:\s*(\S+)", text)
    assert tok and qry, "FlexToken/FlexQuery not found in myconfig.yaml"
    return tok.group(1), qry.group(1)


def test_request_statement_url_is_correct():
    """The broken `### AKE FIX` hardcoded override must be gone."""
    src = Path(ibclient.__file__).read_text()
    assert "portal.flexweb/api/v1/flexQuery" not in src, (
        "ibflex still has the bad hardcoded portal.flexweb URL"
    )
    assert ibclient.REQUEST_URL == (
        "https://gdcdyn.interactivebrokers.com/Universal/servlet/"
        "FlexStatementService.SendRequest"
    )


def test_request_statement_live():
    """Hit IB live: configured token+query should yield a ReferenceCode."""
    token, query_id = _load_flex_creds()
    stmt_access = ibclient.request_statement(token, query_id)
    assert stmt_access.ReferenceCode
    assert re.fullmatch(r"\d+", str(stmt_access.ReferenceCode))
    assert "gdcdyn.interactivebrokers.com" in stmt_access.Url
    print(f"OK ReferenceCode={stmt_access.ReferenceCode} Url={stmt_access.Url}")


if __name__ == "__main__":
    print("ibflex version:", getattr(ibflex, "__version__", "?"))
    print("ibflex file   :", ibclient.__file__)
    print("REQUEST_URL   :", ibclient.REQUEST_URL)
    test_request_statement_url_is_correct()
    print("URL static check passed.")
    test_request_statement_live()
    print("Live fetch passed.")

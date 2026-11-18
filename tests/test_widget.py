import threading
import time

from laria_mcp.server import CallEvent
from laria_mcp.widget import CallLog


def event(**kw):
    base = dict(tool="top_customers", args={"n": 3}, status="ok", duration_ms=12.3, preview="| a |")
    base.update(kw)
    return CallEvent(**base)


def test_status_header():
    log = CallLog()
    log.set_status("serving 3 tools")
    assert "serving 3 tools" in log.header.value


def test_record_appends_escaped_rows_and_trims():
    log = CallLog(max_rows=2)
    for i in range(3):
        log.record(event(args={"n": i}))
    assert len(log.rows.children) == 2
    html = CallLog.format_event(event(preview="<script>"))
    assert "top_customers(n=3)" in html and "&lt;script&gt;" in html and "12 ms" in html


def test_error_rows_show_error_text():
    assert "ValueError" in CallLog.format_event(event(status="error", error="ValueError: bad"))


def click_later(log, index, delay=0.1):
    def run():
        time.sleep(delay)
        box = log.rows.children[-1]
        box.children[index].click()

    threading.Thread(target=run).start()


def test_approve_and_deny_buttons():
    log = CallLog()
    click_later(log, 1)
    assert log.request_approval(event(), timeout=5) is True
    click_later(log, 2)
    assert log.request_approval(event(), timeout=5) is False
    approve, deny = log.rows.children[-1].children[1:]
    assert approve.disabled and deny.disabled


def test_approval_times_out():
    log = CallLog()
    assert log.request_approval(event(), timeout=0.1) is None
    assert "timed out" in log.rows.children[-1].children[0].value

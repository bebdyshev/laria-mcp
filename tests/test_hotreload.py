from laria_mcp.discovery import discover
from laria_mcp.hotreload import HotReloader
from laria_mcp.server import LariaServer


class SpyServer(LariaServer):
    def __init__(self):
        super().__init__("spy")
        self.notified = 0

    def notify_tools_changed(self):
        self.notified += 1


def make(shell):
    server = SpyServer()
    changes = []
    reloader = HotReloader(
        shell,
        server,
        lambda: discover(shell.user_ns.get("In", []), shell.user_ns),
        on_change=changes.append,
    )
    return server, reloader, changes


def test_new_function_triggers_notification(ip):
    shell = ip
    server, reloader, changes = make(shell)
    reloader.start()
    try:
        shell.run_cell("def hr_alpha(x: int) -> int:\n    return x", store_history=True)
        assert "hr_alpha" in server.tool_names
        assert server.notified == 1 and "hr_alpha" in changes[-1]
        shell.run_cell("unrelated = 1", store_history=True)
        assert server.notified == 1
        shell.run_cell("def hr_alpha(x: int, y: int = 0) -> int:\n    return x + y", store_history=True)
        assert server.notified == 2
    finally:
        reloader.stop()


def test_failed_cells_are_ignored_and_stop_unregisters(ip):
    shell = ip
    server, reloader, _ = make(shell)
    reloader.start()
    shell.run_cell("def hr_beta():\n    pass\n1 / 0", store_history=True)
    assert "hr_beta" not in server.tool_names
    reloader.stop()
    shell.run_cell("def hr_gamma():\n    pass", store_history=True)
    assert "hr_gamma" not in server.tool_names

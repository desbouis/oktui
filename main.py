import asyncio

from datetime import datetime

from textual import log
from textual import on
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Static,
)

INSTANCES = [
    ("postgresql-bla9-01"),
    ("redis-bla9-01"),
    ("front-http-bla9-01"),
    ("front-worker-bla9-01"),
    ("front-cron-bla9-01"),
    ("consul-bla9-01"),
    ("consul-bla9-03"),
    ("postgresql-sob7-02"),
    ("redis-sob7-02"),
    ("front-http-sob7-02"),
    ("front-worker-sob7-02"),
    ("consul-sob7-02"),
]

class OKtui(App):
    """OpenStack TUI"""

    CSS_PATH = "main.tcss"

    BINDINGS = [
        ("q", "quit", "Exit"),
        ("d", "toggle_dark", "Toggle theme"),
        ("r", "refresh", "Refresh instances list"),
    ]

    last_update: reactive[str] = reactive("")
    selected_instance_name: reactive[str] = reactive("")


    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(placeholder="Filter instances...", id="filter")
                self.widget_instances_list = DataTable(cursor_type="row", id="instances-list")
                yield self.widget_instances_list
            self.widget_main_panel = Static("Select an instance to show information here...", id="main-panel")
            self.widget_main_panel.border_title = "Instance details"
            yield self.widget_main_panel
            self.widget_status_bar = Static("status bar", id="status-bar")
            yield self.widget_status_bar
        yield Footer()


    def on_mount(self) -> None:
        self.widget_instances_list.add_columns("Instances list")
        self.load_instances()


    def load_instances(self, search: str = "") -> None:
        """Load instances list."""
        self.widget_instances_list.clear()
        log("TODO: execute 'openstack server list'")
        INSTANCES.sort()
        for instance in INSTANCES:
            if search and search.lower() not in instance.lower():
                continue
            self.widget_instances_list.add_row(instance, key=instance)
        self.last_update = datetime.now().strftime("%H:%M:%S")


    @on(Input.Changed, "#filter")
    def filter_instances(self, event) -> None:
        """Filter instances list."""
        self.widget_instances_list.clear()
        self.load_instances(search=event.value)


    @work(exclusive=True)
    async def refresh_instances(self) -> None:
        """Refresh instances list."""
        self.widget_status_bar.update("Refreshing instances list...")
        await asyncio.sleep(1)  # Simulate latency
        search = self.query_one(Input).value
        await self.load_instances(search=search)
        self.notify("Instances list well refreshed!")


    def action_refresh(self) -> None:
        self.refresh_instances()


    @on(DataTable.RowSelected)
    def update_instance_name_value(self, event) -> None:
        """Allow to display instance name in maim panel."""
        if event.data_table != self.widget_instances_list:
            return
        if not event.row_key:
            return
        try:
            row = event.data_table.get_row(event.row_key)
            self.selected_instance_name = str(row[0])
        except Exception as e:
            self.widget_status_bar.update(f"Error: {e}")
            log(f"Error: {e}")


    def watch_last_update(self, value: str) -> None:
        """Display last update when refreshing instances list."""
        if value:
            self.widget_status_bar.update(
                f"Instances list last update: {value}"
            )


    def watch_selected_instance_name(self, value: str) -> None:
        """Display selected instance name."""
        if value:
            log("TODO: execute 'openstack server show'")
            self.widget_main_panel.border_title = f"Details of {value}"
            self.widget_main_panel.update(f"Execute 'openstack server show {value}' and display result here")


if __name__ == "__main__":
    OKtui().run()

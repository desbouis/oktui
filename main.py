import asyncio
from datetime import datetime
import json
import subprocess

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
    instances_list = []


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


    @work(thread=True)
    def load_instances(self, search: str = "") -> None:
        """Load instances list."""
        self.widget_instances_list.clear()
        self.widget_status_bar.update("Loading instances list...")

        try:
            # Execute openstack command if needed
            if not self.instances_list:
                result = subprocess.run(
                    ["openstack", "server", "list", "--os-region-name", "GRA9", "--format", "json", "--sort-column", "Name"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                # Parse json output
                self.instances_list = json.loads(result.stdout)
                # Append a status label property
                for instance in self.instances_list:
                    color = "green" if instance["Status"] == "ACTIVE" else "red" if instance["Status"] == "SHUTOFF" else "yellow"
                    instance["status_label"] = f"[{color}]●[/]"

                # Get last update
                self.last_update = datetime.now().strftime("%H:%M:%S")

            # Filter
            instances_to_display = self.instances_list
            if search:
                instances_to_display = [instance for instance in self.instances_list if search.lower() in instance["Name"].lower()]

            # Load in DataTable
            for instance in instances_to_display:
                self.widget_instances_list.add_row(instance["Name"], key=instance["Name"], label=instance["status_label"])

            self.widget_status_bar.update(f"{len(instances_to_display)} instances [Last update: {self.last_update}]")

        except subprocess.CalledProcessError as e:
            self.widget_status_bar.update(f"Error: {e.stderr.strip()}")
            log(f"Error: {e}")
        except json.JSONDecodeError as e:
            self.widget_status_bar.update(f"Error: Invalid JSON from OpenStack 'server list': {e}")
            log(f"Error: {e}")
        except Exception as e:
            self.widget_status_bar.update(f"Error: {e}")
            log(f"Error: {e}")


    @on(Input.Changed, "#filter")
    def filter_instances(self, event) -> None:
        """Filter instances list."""
        self.widget_instances_list.clear()
        self.load_instances(search=event.value)


    @work(exclusive=True)
    async def refresh_instances(self) -> None:
        """Refresh instances list."""
        self.widget_status_bar.update("Refreshing instances list...")
        self.instances_list = []
        search = self.query_one(Input).value
        self.load_instances(search=search)
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

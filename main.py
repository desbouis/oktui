import asyncio
from datetime import datetime
import json
import os
import pyperclip
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
    Label,
    RichLog,
    Static,
)


class OKtui(App):
    """OpenStack TUI"""

    CSS_PATH = "main.tcss"

    BINDINGS = [
        ("q", "quit", "Exit"),
        ("d", "toggle_dark", "Toggle theme"),
        ("r", "refresh", "Refresh data"),
        ("c", "copy_main_panel", "Copy content"),
    ]

    auth_token = {}
    regions = os.environ["OKTUI_REGIONS"].split()
    last_update: reactive[str] = reactive("")
    selected_instance_name: reactive[str] = reactive("")
    instances_list = []
    instances_details = {}


    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Instances list:", id="instances-list-title")
                yield Input(placeholder="Filter instances...", id="filter")
                self.widget_instances_list = DataTable(header_height=2, show_header=False, cursor_type="row", id="instances-list")
                yield self.widget_instances_list
            self.widget_main_panel = RichLog(id="main-panel", highlight=True, markup=True, auto_scroll=False)
            self.widget_main_panel.border_title = "Select an instance to display details here..."
            yield self.widget_main_panel
            self.widget_status_bar = Static("status bar", id="status-bar")
            yield self.widget_status_bar
        yield Footer()


    def on_mount(self) -> None:
        self.title = "OKtui"
        self.sub_title = f"{' '.join(self.regions)}"
        for env_var in os.environ:
            if env_var.startswith("OS_"):
                self.sub_title += f" - {os.environ[env_var]}"
        self.widget_instances_list.add_columns("instance_name")
        self.fetch_auth_token()
        self.load_instances()


    def fetch_auth_token(self) -> None:
        """
        Fetch auth token to be use with all openstack commands.
        MUST NOT BE CALLED IN THREAD
        """
        try:
            if not self.auth_token:
                cmd = ["openstack", "token", "issue", "--format", "json"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.auth_token = json.loads(result.stdout)
                # Append all required args to pass with all openstack commands
                self.auth_token["auth_args"] = f"--os-token={self.auth_token['id']} --os-cloud= --os-auth-url=https://auth.cloud.ovh.net/v3 --os-auth-type=token"
        except Exception as e:
            self.widget_status_bar.update(f"Error: {e}")
            log(f"Error: {e}")


    @work(thread=True)
    def load_instances(self, search: str = "") -> None:
        """Load instances list."""
        self.widget_instances_list.clear()
        self.widget_status_bar.update("Loading instances list...")

        try:
            # Execute openstack command if needed
            if not self.instances_list:
                for region in self.regions:
                    list_by_region = []
                    cmd = ["openstack", "server", "list", "--os-region-name", region, "--format", "json", "--sort-column", "Name"]
                    cmd[1:1] = self.auth_token["auth_args"].split()
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    # Parse json output
                    list_by_region = json.loads(result.stdout)

                    # Append some useful properties
                    for instance in list_by_region:
                        # status_label
                        color = "green" if instance["Status"] == "ACTIVE" else "red" if instance["Status"] == "SHUTOFF" else "yellow"
                        instance["status_label"] = f"[{color}]●[/]"
                        # region
                        instance["region"] = region

                    # Concat all regions instances
                    self.instances_list += list_by_region

                # Sort by name
                self.instances_list.sort(key=lambda x: x["Name"])

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
    async def refresh_data(self) -> None:
        """Refresh all data."""
        self.widget_status_bar.update("Refreshing data...")
        self.instances_list = []
        self.instances_details = {}
        search = self.query_one(Input).value
        self.load_instances(search=search)
        self.notify("All data will be refreshed!")


    def action_refresh(self) -> None:
        self.refresh_data()


    def action_copy_main_panel(self) -> None:
        """Copy content of main panel"""
        try:
            content = "```\n"
            content += self.widget_main_panel.border_title
            content += "\n\n"
            content += self.instances_details[self.selected_instance_name]
            content += "```\n"
            pyperclip.copy(content)
            self.notify("Content copied to clipboard!", severity="information")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")


    @on(DataTable.RowSelected)
    def update_instance_name_value(self, event) -> None:
        """Update selected instance name allowing to use it in openstack commands."""
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
            self.widget_main_panel.border_title = f"Executing command..."
            self.widget_main_panel.clear()
            self.fetch_instance_details(value)


    @work(thread=True)
    def fetch_instance_details(self, value: str) -> None:
        try:
            region = next((instance for instance in self.instances_list if instance["Name"] == value), None)["region"]
            cmd = ["openstack", "server", "show", value, "--os-region-name", region, "--format", "table"]
            if not self.instances_details.get(value):
                cmd_exec = cmd.copy()
                cmd_exec[1:1] = self.auth_token["auth_args"].split()
                result = subprocess.run(cmd_exec, capture_output=True, text=True, check=True)
                self.instances_details[value] = result.stdout
            self.widget_main_panel.border_title = f"{' '.join(cmd)}"
            self.widget_main_panel.write(self.instances_details[value])
        except Exception as e:
            self.widget_main_panel.clear()
            self.widget_main_panel.write(f"Error: {e}")
            log(f"Error: {e}")


if __name__ == "__main__":
    OKtui().run()

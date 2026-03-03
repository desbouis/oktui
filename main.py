import asyncio
from datetime import datetime
import json
import os
import pyperclip
import subprocess

from textual import log
from textual import on
from textual import screen
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
    TabbedContent,
    TabPane,
)


class OKtui(App):
    """OpenStack TUI"""

    CSS_PATH = "main.tcss"

    BINDINGS = [
        ("q", "quit", "Exit"),
        ("d", "toggle_dark", "Toggle theme"),
        ("M", "maximize_output", "Maximize"),
        ("R", "refresh_all", "Refresh all"),
        ("r", "refresh_active_tab", "Refresh tab"),
        ("c", "copy_main_panel", "Copy content"),
    ]

    auth_token = {}
    regions = os.environ["OKTUI_REGIONS"].split()
    last_update: reactive[str] = reactive("")
    selected_instance_name: reactive[str] = reactive("")
    instances_list = []
    cache_server_show = {}
    cache_console_log_show = {}
    cache_server_event_list = {}
    initial_labels = {
        "sidebar": "Instances list:",
        "filter": "Filter instances...",
        "title_server_show": "Select instance to display details here...",
        "title_console_log_show": "Select instance to display logs here...",
        "title_server_event_list": "Select instance to display events here...",
        "status_bar": "Loading...",
    }


    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():

            with Vertical(id="sidebar"):
                yield Label(self.initial_labels["sidebar"], id="instances-list-title")
                yield Input(placeholder=self.initial_labels["filter"], id="filter")
                self.widget_instances_list = DataTable(header_height=2, show_header=False, cursor_type="row", id="instances-list")
                yield self.widget_instances_list

            with TabbedContent(initial="tab-server-show", id="main-tabbed-content"):
                with TabPane("Server show", id="tab-server-show"):
                    self.widget_content_server_show = RichLog(id="content-server-show", highlight=True, markup=False, auto_scroll=False)
                    self.widget_content_server_show.border_title = self.initial_labels["title_server_show"]
                    yield self.widget_content_server_show
                with TabPane("Console log show", id="tab-console-log-show"):
                    self.widget_content_console_log_show = RichLog(id="content-console-log-show", highlight=True, markup=False, auto_scroll=True)
                    self.widget_content_console_log_show.border_title = self.initial_labels["title_console_log_show"]
                    yield self.widget_content_console_log_show
                with TabPane("Server event list", id="tab-server-event-list"):
                    self.widget_content_server_event_list = RichLog(id="content-server-event-list", highlight=True, markup=False, auto_scroll=False)
                    self.widget_content_server_event_list.border_title = self.initial_labels["title_server_event_list"]
                    yield self.widget_content_server_event_list

        self.widget_status_bar = Static(self.initial_labels["status_bar"], id="status-bar")
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
    async def refresh_all(self) -> None:
        """Refresh all data."""
        self.widget_status_bar.update("Refreshing data...")
        # Clean stored data
        self.instances_list = []
        self.cache_server_show = {}
        self.cache_console_log_show = {}
        self.cache_server_event_list = {}
        self.selected_instance_name = ""
        # Reset interface
        self.widget_instances_list.clear()
        self.widget_content_server_show.clear()
        self.widget_content_server_show.border_title = self.initial_labels["title_server_show"]
        self.widget_content_server_show.border_subtitle = ""
        self.widget_content_console_log_show.clear()
        self.widget_content_console_log_show.border_title = self.initial_labels["title_console_log_show"]
        self.widget_content_console_log_show.border_subtitle = ""
        self.widget_content_server_event_list.clear()
        self.widget_content_server_event_list.border_title = self.initial_labels["title_server_event_list"]
        self.widget_content_server_event_list.border_subtitle = ""
        search = self.query_one(Input).value
        self.load_instances(search=search)
        self.notify("All data will be refreshed!")


    @work(exclusive=True)
    async def refresh_active_tab(self) -> None:
        """Refresh content in active tab."""
        self.notify("Refreshing content in active tab...", severity="information")
        try:
            if self.selected_instance_name:
                tab = self.query_one("#main-tabbed-content", TabbedContent)
                if tab.active == "tab-server-show":
                    self.cache_server_show[self.selected_instance_name] = {}
                    self.widget_content_server_show.clear()
                    self.widget_content_server_show.border_title = f"Executing command..."
                    self.widget_content_server_show.border_subtitle = ""
                    self.fetch_server_show(self.selected_instance_name)
                if tab.active == "tab-console-log-show":
                    self.cache_console_log_show[self.selected_instance_name] = {}
                    self.widget_content_console_log_show.clear()
                    self.widget_content_console_log_show.border_title = f"Executing command..."
                    self.widget_content_console_log_show.border_subtitle = ""
                    self.fetch_console_log_show(self.selected_instance_name)
                if tab.active == "tab-server-event-list":
                    self.cache_server_event_list[self.selected_instance_name] = {}
                    self.widget_content_server_event_list.clear()
                    self.widget_content_server_event_list.border_title = f"Executing command..."
                    self.widget_content_server_event_list.border_subtitle = ""
                    self.fetch_server_event_list(self.selected_instance_name)
            else:
                self.notify("Nothing to refresh!", severity="information")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")


    def action_maximize_output(self) -> None:
        self.screen.maximize(self.query_one("#main-tabbed-content", TabbedContent))


    def action_refresh_all(self) -> None:
        self.refresh_all()


    def action_refresh_active_tab(self) -> None:
        self.refresh_active_tab()


    def action_copy_main_panel(self) -> None:
        """Copy content of main panel"""
        try:
            tab = self.query_one("#main-tabbed-content", TabbedContent)
            content = ""
            if tab.active == "tab-server-show":
                content += self.widget_content_server_show.border_title
                content += "\n\n"
                content += self.cache_server_show[self.selected_instance_name]["output"]
            if tab.active == "tab-console-log-show":
                content += self.widget_content_console_log_show.border_title
                content += "\n\n"
                content += self.cache_console_log_show[self.selected_instance_name]["output"]
            if tab.active == "tab-server-event-list":
                content += self.widget_content_server_event_list.border_title
                content += "\n\n"
                content += self.cache_server_event_list[self.selected_instance_name]["output"]
            pyperclip.copy(f"```\n{content}```\n")
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
            # Clean tabs
            self.widget_content_server_show.border_title = f"Executing command..."
            self.widget_content_server_show.border_subtitle = ""
            self.widget_content_server_show.clear()
            self.widget_content_console_log_show.border_title = f"Executing command..."
            self.widget_content_console_log_show.border_subtitle = ""
            self.widget_content_console_log_show.clear()
            self.widget_content_server_event_list.border_title = f"Executing command..."
            self.widget_content_server_event_list.border_subtitle = ""
            self.widget_content_server_event_list.clear()
            # Go to server show tab when selecting an instance
            self.query_one("#main-tabbed-content", TabbedContent).active = "tab-server-show"
            # Execute server show
            self.fetch_server_show(value)


    @on(TabbedContent.TabActivated)
    def exec_command(self, event) -> None:
        """Switch to a new tab."""
        try:
            if self.selected_instance_name:
                if event.tabbed_content.active == "tab-server-show":
                    self.fetch_server_show(self.selected_instance_name)
                if event.tabbed_content.active == "tab-console-log-show":
                    self.fetch_console_log_show(self.selected_instance_name)
                if event.tabbed_content.active == "tab-server-event-list":
                    self.fetch_server_event_list(self.selected_instance_name)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            log(f"Error: {e}")


    @work(thread=True)
    def fetch_server_show(self, value: str) -> None:
        """Execute 'server show'."""
        try:
            region = next((instance for instance in self.instances_list if instance["Name"] == value), None)["region"]
            cmd = ["openstack", "server", "show", value, "--os-region-name", region, "--format", "table"]
            if not self.cache_server_show.get(value):
                self.notify("Execute 'server show'")
                cmd_exec = cmd.copy()
                cmd_exec[1:1] = self.auth_token["auth_args"].split()
                result = subprocess.run(cmd_exec, capture_output=True, text=True, check=True)
                self.cache_server_show[value] = {
                    "output": result.stdout,
                    "last_update": datetime.now().strftime("%H:%M:%S"),
                }
            self.widget_content_server_show.border_title = f"{' '.join(cmd)}"
            self.widget_content_server_show.border_subtitle = f"Last update: {self.cache_server_show[value]['last_update']}"
            self.widget_content_server_show.write(self.cache_server_show[value]["output"])
        except Exception as e:
            self.widget_content_server_show.clear()
            self.widget_content_server_show.write(f"Error: {e}")
            log(f"Error: {e}")


    @work(thread=True)
    def fetch_console_log_show(self, value: str) -> None:
        """Execute 'console log show'."""
        try:
            region = next((instance for instance in self.instances_list if instance["Name"] == value), None)["region"]
            cmd = ["openstack", "console", "log", "show", value, "--os-region-name", region]
            if not self.cache_console_log_show.get(value):
                self.notify("Execute 'console log show'")
                cmd_exec = cmd.copy()
                cmd_exec[1:1] = self.auth_token["auth_args"].split()
                result = subprocess.run(cmd_exec, capture_output=True, text=True, check=True)
                self.cache_console_log_show[value] = {
                    "output": result.stdout,
                    "last_update": datetime.now().strftime("%H:%M:%S"),
                }
            self.widget_content_console_log_show.border_title = f"{' '.join(cmd)}"
            self.widget_content_console_log_show.border_subtitle = f"Last update: {self.cache_console_log_show[value]['last_update']}"
            self.widget_content_console_log_show.write(self.cache_console_log_show[value]["output"])
        except Exception as e:
            self.widget_content_console_log_show.clear()
            self.widget_content_console_log_show.write(f"Error: {e}")
            log(f"Error: {e}")


    @work(thread=True)
    def fetch_server_event_list(self, value: str) -> None:
        """Execute 'server event list'."""
        try:
            region = next((instance for instance in self.instances_list if instance["Name"] == value), None)["region"]
            cmd = ["openstack", "server", "event", "list", value, "--os-region-name", region, "--format", "table"]
            if not self.cache_server_event_list.get(value):
                self.notify("Execute 'server event list'")
                cmd_exec = cmd.copy()
                cmd_exec[1:1] = self.auth_token["auth_args"].split()
                result = subprocess.run(cmd_exec, capture_output=True, text=True, check=True)
                self.cache_server_event_list[value] = {
                    "output": result.stdout,
                    "last_update": datetime.now().strftime("%H:%M:%S"),
                }
            self.widget_content_server_event_list.border_title = f"{' '.join(cmd)}"
            self.widget_content_server_event_list.border_subtitle = f"Last update: {self.cache_server_event_list[value]['last_update']}"
            self.widget_content_server_event_list.write(self.cache_server_event_list[value]["output"])
        except Exception as e:
            self.widget_content_server_event_list.clear()
            self.widget_content_server_event_list.write(f"Error: {e}")
            log(f"Error: {e}")


if __name__ == "__main__":
    OKtui().run()

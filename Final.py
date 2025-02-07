import time
import asyncio
import json
import os
import random
import re
import socket
import threading
import flet as ft
import sys
import subprocess
import flet_lottie
from cryptography.fernet import Fernet
from pyngrok import ngrok

class Swiftshare:
    def __init__(self):
        self.selected_file = ""
        self.host = "localhost"
        self.port = random.randint(1024, 65535)
        self.key = b"2heTHvvD6E9jz3HXTEwRvPPGj0by5BNnDG6l7UYzsoc="
        self.cipher = Fernet(self.key)
        self.page = None

    def connection_code(self, public_url):
        data = f"{public_url}"
        code = self.cipher.encrypt(data.encode())
        return code.decode()

    def initialize(self, page: ft.Page):
        self.port = random.randint(1024, 65535)
        public_url = ngrok.connect(self.port, "tcp")
        print(public_url)
        self.code = self.connection_code(public_url)
        print(f"Connection code: \033[2;32m{self.code}\033[0m")

    def listen_receiver(self, page: ft.Page):
        try:
            # Create and bind the socket
            self.sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sender.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
            self.sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
            self.sender.bind((self.host, self.port))
            self.sender.listen(1)
            print(f"Server is running on {self.host}:{self.port}. Waiting for a connection...")

            # Accept one connection and then exit
            self.sender_conn, sender_addr = self.sender.accept()
            print(f"Connected to receiver: {sender_addr}")
            self.fdbk_txt_gcp.value = "Connected to receiver"
            page.update()
            self.sending_file_page(page)

        except Exception as e:
            print(f"Server error: {e}")
        finally:
            # Clean up
            self.sender.close()
            print("Server shut down.")

    def update_progress_ui(self, progress, bytes_transferred, total_size):
        """Update UI elements on the main thread."""
        if hasattr(self, 'data_pb'):
            self.data_pb.value = progress
        if hasattr(self, 'data_txt'):
            self.data_txt.value = (
                f"Data Transferred: {bytes_transferred / 1024 / 1024:.2f}MB/"
                f"{total_size / 1024 / 1024:.2f}MB"
            )
        if self.page:
            self.page.update()

    def send_file(self, sender_conn, page: ft.Page):
        """Send file with progress updates."""
        try:
            print("Sending file metadata")
            self.page = page

            self.file_name = self.selected_file[0].name
            self.file_size = self.selected_file[0].size

            file_info = {
                "name": self.file_name,
                "path": self.selected_file[0].path,
                "size": self.file_size
            }
            file_info_json = json.dumps(file_info).encode()
            sender_conn.sendall(file_info_json.ljust(1024))

            file = self.selected_file[0].path
            total_size = os.path.getsize(file)
            bytes_sent = 0

            start_time = time.time()
            with open(file, "rb") as f:
                while True:
                    file_data = f.read(1048576)  # Read 1MB chunks
                    if not file_data:
                        break

                    sender_conn.send(file_data)
                    bytes_sent += len(file_data)
                    progress = bytes_sent / total_size

                    # Schedule UI update using page.update()
                    self.update_progress_ui(progress, bytes_sent, total_size)

            self.sent_time = round(time.time()-start_time, 2)
            print("\nFile Sent")
            sender_conn.close()

            self.file_sent_page(page)

        except Exception as e:
            print(f"Error sending file: {e}")
            sender_conn.close()

    def receive_file(self, page: ft.Page):
        """Receive file with progress updates."""
        try:
            folder_path = os.path.join(os.path.expanduser("~"), "Downloads", "SwiftShare")
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            file_info_json = self.receiver.recv(1024).decode().strip()
            file_info = json.loads(file_info_json)
            self.received_file_name = file_info["name"]
            self.received_file_size = file_info["size"]
            bytes_received = 0

            file_path = os.path.join(folder_path, self.received_file_name)

            start_time = time.time()
            with open(file_path, "wb") as f:
                while True:
                    file_data = self.receiver.recv(1048576)
                    if not file_data:
                        break

                    f.write(file_data)
                    bytes_received += len(file_data)
                    progress = bytes_received / self.received_file_size

                    # Schedule UI update
                    self.update_progress_ui(progress, bytes_received, self.received_file_size)

            self.receive_time = round(time.time()-start_time, 2)
            print(f"File saved to: {file_path}")
            self.receiver.close()

            self.file_received_page(page)

        except Exception as e:
            print(f"Error receiving file: {e}")
            if hasattr(self, 'receiver'):
                self.receiver.close()

    def connect_to_sender(self, page, code):
        print("We are into the fucntion")
        pattern = r'"(.*?)"'
        if not code:
            self.fdbk_txt_rcp.value = "Please enter a valid connection code."
        else:
            self.fdbk_txt_rcp.value = "Attempting to connect..."
            page.update()
            try:
                decrypted_data = self.cipher.decrypt(code.encode()).decode()
                matches = re.findall(pattern, decrypted_data)
                url = matches[0]
                cleaned_url = str(url).removeprefix("tcp://")
                final_url = cleaned_url.split(":")
                print(f"{final_url} is the final url")
                host = final_url[0]
                port = int(final_url[1])
                self.receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
                self.receiver.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
                print("Server has started")
                self.receiver.connect((host, port))
                self.fdbk_txt_rcp.value = "Connected to the Sender"
                print("Connected to the Sender")
                page.update()
                self.receiving_file_page(page)
                print("Still in connect to sender")

            except socket.timeout:
                self.fdbk_txt_rcp.value = "Connection timed out. Please try again."
            except socket.gaierror:
                self.fdbk_txt_rcp.value = "Invalid address. Please check the connection code."
            except Exception as e:
                self.fdbk_txt_rcp.value = f"Failed to connect: {str(e)}"
                print(f"Connection error: {str(e)}")  # Debug print
        page.update()

    async def skeleton(self, page: ft.Page):
        page.title = "Swift Share"
        page.window.height = 700
        page.window.width = 1000
        page.window.resizable = False
        page.window.max_width = 1000
        page.window.max_height = 700
        page.fonts = {
            "Gugi": r'C:\Users\rudra\Documents\Code\Python\Programs\Swift Share\File_Share\UI File_Share\font\Gugi\Gugi-Regular.ttf',
            "Electrolize": r'C:\Users\rudra\Documents\Code\Python\Programs\Swift Share\File_Share\UI File_Share\font\Electrolize\Electrolize-Regular.ttf',
            "Inter": r'C:\Users\rudra\Documents\Code\Python\Programs\Swift Share\File_Share\UI File_Share\font\Inter\Inter-VariableFont_opsz,wght.ttf'
        }

        # Reset all padding and spacing
        page.padding = 0
        page.spacing = 0

        # Background container with a Column for dynamic controls
        self.bg = ft.Container(
            width=1000,
            height=623,
            bgcolor="#121212",
            padding=ft.Padding(left=30, right=50, top=35, bottom=20),
            margin=0,
            content=ft.Column(
                spacing=0
            )
        )

        # Bottom bar container
        bottom_bar = ft.Container(
            width=1000,
            height=40,
            bgcolor="#1c1c1c",
            border_radius=ft.BorderRadius(
                top_left=12,
                top_right=12,
                bottom_left=6,
                bottom_right=6
            ),
            border=ft.border.all(1, "#2d2d2d"),
            padding=ft.Padding(left=35, right=25, top=0, bottom=0),
            margin=0,
            content=ft.Row(
                alignment="spaceBetween",
                spacing=0,
                controls=[
                    ft.Text("Version 1.0.0", color="white", opacity=0.4),
                    ft.Text("© 2025 Swift Share", color="white", opacity=0.4),
                ]
            )
        )

        # Add background and bottom bar to a column with explicit settings
        layout = ft.Column(
            spacing=0,
            controls=[
                self.bg,
                bottom_bar
            ]
        )

        page.add(layout)

        # Pass the page object to main_page
        self.main_page(page)

    def main_page(self, page: ft.Page):
        card = ft.Card(content=ft.Container(
            width=500,
            height=550,
            bgcolor="#1c1c1c",
            border_radius=10,
            padding=10,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Image(
                        src=r'C:\Users\rudra\Documents\Code\Python\Programs\Swift Share\File_Share\UI File_Share\Images\File Share 2.svg'
                    )
                ]
            )
        ))

        icon = ft.Image(
            src=r'C:\Users\rudra\Documents\Code\Python\Programs\Swift Share\File_Share\UI File_Share\Icon\final icon.png',
            width=80,
            height=80,
            fit=ft.ImageFit.CONTAIN
        )

        title = ft.Container(
            content=ft.Text("Swift Share", size=60, font_family="Gugi"),
            margin=ft.margin.only(left=-5, right=0, top=0, bottom=0)
        )
        tag_line = ft.Text("Fast & Secure File Transfer For Everyone", size=18, font_family="Electrolize")
        text_spacer = ft.Container(width=38)

        title_stack = ft.Column(
            spacing=0,  # No spacing between rows
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=0,  # No spacing between the icon and title
                    tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            content=icon,
                            margin=ft.margin.all(0),  # No margin for the icon
                            padding=ft.Padding(0, 0, 0, 0),  # No padding for the icon
                        ),
                        ft.Container(
                            content=title,
                            margin=ft.margin.all(-8),  # No margin for the title
                            padding=ft.Padding(0, 0, 0, 0),  # No padding for the title
                        ),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[text_spacer, tag_line]
                ),
            ],
        )

        send_btn = ft.FilledButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color="#ffffff",
            text="Send",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=2,
                        bottom_right=2
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda e: self.select_file(page)
        )

        recv_btn = ft.FilledButton(
            icon=ft.Icons.FILE_DOWNLOAD_ROUNDED,
            icon_color="#ffffff",
            text="Receive",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=2,
                        top_right=2,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.receive_code_page(page)
        )

        button_spacer = ft.Container(width=50)

        button_stack = ft.Column(
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=0,
                    controls=[button_spacer, send_btn]
                ),
                ft.Row(
                    spacing=0,
                    controls=[button_spacer, recv_btn]
                )
            ]
        )

        bottom_spacer = ft.Container(height=0)

        # Main layout using Row with Expanded
        layout = ft.Row(
            spacing=0,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                card,
                ft.Container(
                    content=ft.Column(
                        spacing=80,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            title_stack,
                            button_stack,
                            bottom_spacer
                        ],
                    )
                )
            ],
        )

        self.bg.content.controls.append(layout)
        page.update()

    def back_to_main(self, page: ft.Page):
        self.bg.content.clean()
        if self.selected_file:
            self.selected_file = ""
            print("Selection Cancelled")
        self.main_page(page)

    def cancel_file(self, page: ft.Page):
        # Reset info_cont to its original state with the info text
        self.info_cont.content = ft.Column(
            controls=[self.info_text],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.selected_file = ""

        print("Selection Cancelled")

        # Reset the proceed button to disabled state
        self.proceed_btn.mouse_cursor = ft.MouseCursor.NO_DROP
        self.proceed_btn.content.bgcolor = "#3a3a3a"
        self.proceed_btn.content.content.controls[0].color = "#a1a1a1"
        self.proceed_btn.content.content.controls[1].color = "#a1a1a1"
        self.proceed_btn.content.on_click = None

        # Reset the upload button to enabled state
        self.upload_file_btn.mouse_cursor = ft.MouseCursor.CLICK
        self.upload_file_btn.content.bgcolor = "#2c2c2c"
        self.upload_file_btn.content.content.controls[0].color = "#ffffff"
        self.upload_file_btn.content.content.controls[1].color = "#ffffff"
        self.upload_file_btn.content.on_click = lambda e: self.file_picker.pick_files(allow_multiple=False)

        page.update()

    def show_file_card(self, page: ft.Page):
        file_info = self.selected_file[0]

        self.proceed_btn.mouse_cursor = ft.MouseCursor.CLICK  # Change cursor to pointer
        self.proceed_btn.content.bgcolor = "#2c2c2c"  # Change to active background color
        self.proceed_btn.content.content.controls[0].color = "#ffffff"  # Change text color
        self.proceed_btn.content.content.controls[1].color = "#ffffff"  # Change icon color
        self.proceed_btn.content.on_click = lambda e: self.generate_code_page(page)

        self.upload_file_btn.mouse_cursor = ft.MouseCursor.NO_DROP
        self.upload_file_btn.content.bgcolor = "#3a3a3a"
        self.upload_file_btn.content.content.controls[0].color = "#a1a1a1"
        self.upload_file_btn.content.content.controls[1].color = "#a1a1a1"
        self.upload_file_btn.content.on_click = None

        cancel_btn = ft.IconButton(
            icon=ft.Icons.CANCEL_ROUNDED,
            icon_color="white",
            on_click=lambda e: self.cancel_file(page)
        )

        # Create file card with file information
        file_card = ft.Card(
            content=ft.Container(
                width=800,  # Fixed width for the container
                bgcolor="#1c1c1c",
                border_radius=10,
                padding=15,
                border=ft.border.all(1, "#2d2d2d"),
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(
                                    f"File: {file_info.name}",
                                    size=16,
                                    color="white",
                                    max_lines=1,
                                    no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    width=600,  # Set width for text clipping
                                ),
                                ft.Text(
                                    f"Size: {file_info.size / 1024:.1f} KB",
                                    size=14,
                                    color="#808080",
                                ),
                            ],
                            spacing=6,
                        ),
                        cancel_btn,
                    ],
                    alignment="spaceBetween",  # Align content on both ends
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,  # Vertically center elements
                ),
            )
        )

        # Update the info_txt reference with the card
        self.info_cont.content = file_card
        page.update()

    def select_file(self, page: ft.Page):
        self.bg.content.clean()

        self.file_picker = ft.FilePicker()
        page.overlay.append(self.file_picker)

        self.selected_file = ""

        def on_select_file(e):
            self.selected_file = e.files
            if self.selected_file:
                self.show_file_card(page)

        self.file_picker.on_result = on_select_file

        title = ft.Text("Select a file to send", size=40, font_family="Inter")

        self.upload_file_btn = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.UPLOAD_FILE_ROUNDED, color="#ffffff"),
                        ft.Text("Upload", color="#ffffff", weight="w600"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                width=230,
                height=50,
                bgcolor="#2c2c2c",
                border_radius=ft.border_radius.only(
                    top_left=10,
                    top_right=10,
                    bottom_left=10,
                    bottom_right=10,
                ),
                padding=ft.padding.all(10),
                ink=True,
                on_click=lambda e: self.file_picker.pick_files(allow_multiple=False)
            )
        )

        upper_stack = ft.Column(
            controls=[
                title,
                self.upload_file_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )

        self.info_text = ft.Text("No file is selected", color="white", opacity=0.4)
        # Create a container to hold either the info text or file card
        self.info_cont = ft.Container(
            content=ft.Column(
                controls=[self.info_text],  # Initialize with the default text
                alignment=ft.MainAxisAlignment.CENTER,  # Center items vertically
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # Center items horizontally
            ),
            alignment=ft.alignment.center,
        )

        back_to_main_btn = ft.FilledButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color="#ffffff",
            text="Back to main",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.back_to_main(page)
        )

        self.proceed_btn = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.NO_DROP,
            content=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text("Proceed", color="#a1a1a1", weight="w600"),
                        ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color="#a1a1a1"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                width=230,
                height=50,
                bgcolor="#3a3a3a",
                border_radius=ft.border_radius.only(
                    top_left=10,
                    top_right=10,
                    bottom_left=10,
                    bottom_right=10,
                ),
                padding=ft.padding.all(10),
                ink=True,
                on_click=None,
            )
        )

        button_stack = ft.Row(
            controls=[back_to_main_btn, self.proceed_btn],
            alignment="SpaceBetween"
        )

        centered_content = ft.Container(
            padding=ft.Padding(top=20, bottom=60, left=50, right=50),
            content=ft.Column(
                [
                    upper_stack,
                    self.info_cont,  # Now this will be replaced with the card when a file is selected
                    button_stack
                ],
                spacing=25,
                alignment="SpaceAround",
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            width=self.bg.width,
            height=self.bg.height,
        )

        self.bg.content.controls.append(centered_content)
        page.update()

    async def copy_to_clipboard(self, e):
        page = e.page
        page.set_clipboard(self.code)
        self.copy_btn.icon = None
        self.copy_btn.text = "Copied"
        page.update()

        await asyncio.sleep(1)

        self.copy_btn.icon = ft.Icons.COPY
        self.copy_btn.text = "Copy to Clipboard"
        page.update()

    def generate_code_page(self, page: ft.Page):
        self.initialize(page)
        self.bg.content.clean()

        title = ft.Text("Send this code to the receiver", size=40)

        code_display = ft.TextField(
            value=self.code,
            read_only=True,
            width=600,
            multiline=True,
            color="green",
            bgcolor="#2c2c2c",
            border_color="#a3a3a3",
            border_width=0.5,
            border_radius=15,
            text_size=18,
            max_lines=4
        )

        back_to_main_btn = ft.FilledButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color="#ffffff",
            text="Back to main",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.back_to_main(page)
        )

        self.copy_btn = ft.FilledButton(
            icon=ft.Icons.COPY,
            icon_color= "#ffffff",
            text="Copy to Clipboard",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=self.copy_to_clipboard
        )

        self.fdbk_txt_gcp = ft.Text("Waiting for a connection",
                                    color="#FFBF00",
                                    size=17,
                                    weight="w500"
                                    )

        layout = ft.Container(
            width=800,
            height=500,
            bgcolor="#1c1c1c",
            border_radius=15,
            border=ft.border.all(2, "#2d2d2d"),
            padding=20,
            content=ft.Column(
                spacing=40,
                controls=[
                    title,
                    code_display,
                    ft.Row(controls=[back_to_main_btn, self.copy_btn],
                           alignment=ft.MainAxisAlignment.SPACE_AROUND
                           ),
                    self.fdbk_txt_gcp
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        # Create a centered container to hold the layout
        centered_content = ft.Container(
            padding=ft.Padding(top=20, bottom=60, left=50, right=50),
            content=ft.Column(
                [layout],
                spacing=25,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            width=self.bg.width,
            height=self.bg.height,
        )

        self.bg.content.controls.append(centered_content)
        page.update()
        self.listen_receiver(page)

    def receive_code_page(self, page: ft.Page):
        self.bg.content.clean()

        title = ft.Text("Enter code to connect to the sender", size=40)

        code_display = ft.TextField(
            width=600,
            multiline=True,
            color="green",
            bgcolor="#2c2c2c",
            border_color="#a3a3a3",
            border_width=0.5,
            border_radius=15,
            text_size=18,
        )

        back_to_main_btn = ft.FilledButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color="#ffffff",
            text="Back to main",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.back_to_main(page)
        )

        # Create a function to handle the connect button click
        def handle_connect(e):
            # Get the current value from the text field when the button is clicked
            code = code_display.value.strip()
            self.connect_to_sender(page, code)

        connect_btn = ft.FilledButton(
            icon=ft.Icons.PRIVATE_CONNECTIVITY_ROUNDED,
            icon_color= "#ffffff",
            text="Connect",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=handle_connect  # Use the new handler function
        )

        self.fdbk_txt_rcp = ft.Text("",
                                    color="#FFBF00",
                                    size=17,
                                    weight="w500"
                                    )

        layout = ft.Container(
            width=800,
            height=500,
            bgcolor="#1c1c1c",
            border_radius=15,
            border=ft.border.all(2, "#2d2d2d"),
            padding=20,
            content=ft.Column(
                spacing=40,
                controls=[
                    title,
                    code_display,
                    ft.Row(controls=[back_to_main_btn, connect_btn],
                           alignment=ft.MainAxisAlignment.SPACE_AROUND
                           ),
                    self.fdbk_txt_rcp  # Add the feedback text to the layout
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        # Create a centered container to hold the layout
        centered_content = ft.Container(
            padding=ft.Padding(top=20, bottom=60, left=50, right=50),
            content=ft.Column(
                [layout],
                spacing=25,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            width=self.bg.width,
            height=self.bg.height,
        )

        self.bg.content.controls.append(centered_content)
        page.update()

    def sending_file_page(self, page: ft.Page):
        self.bg.content.clean()

        # Title at the top
        title = ft.Text("Sending Data", size=50, text_align=ft.TextAlign.CENTER)

        # Animation centered below title
        file_animation = flet_lottie.Lottie(
            src="https://lottie.host/e7f2bdeb-62cf-4418-9203-bf0968cf81c8/9yHOADlft9.json",
            width=250,
            height=250,
            fit=ft.ImageFit.CONTAIN,
            repeat=True,
            animate=True,
        )

        wait_txt = ft.Text(
            "Please wait while we send the data",
            size=20,
            opacity=0.4,
            text_align=ft.TextAlign.CENTER
        )

        self.data_pb = ft.ProgressBar(width=500)
        self.data_txt = ft.Text("Data Sent: 0MB/0MB", text_align=ft.TextAlign.CENTER)

        # Main container with better spacing
        layout = ft.Container(
            width=self.bg.width,
            height=self.bg.height,
            content=ft.Column(
                controls=[
                    ft.Container(height=10),
                    title,
                    file_animation,
                    ft.Container(height=10),
                    self.data_pb,
                    ft.Container(height=15),
                    self.data_txt,
                    ft.Container(height=80),
                    wait_txt
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.bg.content.controls.append(layout)
        page.update()

        send_tread = threading.Thread(
            target=self.send_file,
            args=(self.sender_conn, page),
            daemon=True
        )

        send_tread.start()

        print("Completed")

    def receiving_file_page(self, page: ft.Page):
        """Initialize receiving file page."""
        self.page = page  # Store page reference
        self.bg.content.clean()

        # Title at the top
        title = ft.Text("Receiving Data", size=50, text_align=ft.TextAlign.CENTER)

        # Animation centered below title
        file_animation = flet_lottie.Lottie(
            src="https://lottie.host/e7f2bdeb-62cf-4418-9203-bf0968cf81c8/9yHOADlft9.json",
            width=250,
            height=250,
            fit=ft.ImageFit.CONTAIN,
            repeat=True,
            animate=True,
        )

        wait_txt = ft.Text(
            "Please wait while we receive the data",
            size=20,
            opacity=0.4,
            text_align=ft.TextAlign.CENTER
        )

        self.data_pb = ft.ProgressBar(width=500, value=0)
        self.data_txt = ft.Text("Data Transferred: 0MB/0MB", text_align=ft.TextAlign.CENTER)

        # Main container with better spacing
        layout = ft.Container(
            width=self.bg.width,
            height=self.bg.height,
            content=ft.Column(
                controls=[
                    ft.Container(height=10),
                    title,
                    file_animation,
                    ft.Container(height=10),
                    self.data_pb,
                    ft.Container(height=15),
                    self.data_txt,
                    ft.Container(height=80),
                    wait_txt
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.bg.content.controls.append(layout)
        page.update()

        receive_thread = threading.Thread(
            target=self.receive_file,
            args=(page,),
            daemon=True
        )
        receive_thread.start()

    def back_to_home(self, page: ft.Page):
        self.bg.content.clean()
        self.main_page(page)

    def file_sent_page(self, page: ft.Page):
        self.bg.content.clean()

        # Title and animation based on transfer type
        title_text = "File Sent Successfully"
        title = ft.Text(title_text, size=40, text_align=ft.TextAlign.CENTER)

        # Success animation
        success_animation = flet_lottie.Lottie(
            src="https://lottie.host/1da69d8e-0306-4815-9f5d-570d3fefa4e0/WSRBNsIJc7.json",
            width=250,
            height=250,
            fit=ft.ImageFit.CONTAIN,
            repeat=False,
            animate=True,
        )

        # File details
        file_name = ft.Text(
            f"File Name: {self.file_name}",
            size=18,
            opacity=0.7,
            text_align=ft.TextAlign.CENTER
        )
        file_size = ft.Text(
            f"File Size: {self.file_size / 1024:.1f} KB",
            size=18,
            opacity=0.7,
            text_align=ft.TextAlign.CENTER
        )
        time_taken = ft.Text(
            f"Time Taken: {self.sent_time}s",
            size=18,
            opacity=0.7,
            text_align=ft.TextAlign.CENTER
        )
        # Buttons
        back_to_main_btn = ft.FilledButton(
            icon=ft.Icons.HOME_ROUNDED,
            icon_color= "#ffffff",
            text="Back to Main",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.back_to_home(page)
        )

        repeat_btn = ft.FilledButton(
            icon=ft.Icons.REPEAT_ROUNDED,
            icon_color= "#ffffff",
            text="Transfer Another File",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.select_file(page)
        )

        # Main container
        layout = ft.Container(
            width=self.bg.width,
            height=self.bg.height,
            content=ft.Column(
                controls=[
                    ft.Container(height=20),
                    title,
                    success_animation,
                    ft.Container(height=20),
                    file_name,
                    file_size,
                    time_taken,
                    ft.Container(height=40),
                    ft.Row(
                        controls=[back_to_main_btn, repeat_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20
                    )
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.bg.content.controls.append(layout)
        page.update()

    def open_folder(self, e):
        """Opens the folder containing the received file."""
        folder_path = os.path.join(os.path.expanduser("~"), "Downloads", "SwiftShare")
        if sys.platform == "win32":
            subprocess.Popen(f'explorer "{folder_path}"')  # Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])  # macOS
        else:
            subprocess.Popen(["xdg-open", folder_path])  # Linux

    def file_received_page(self, page: ft.Page):
        self.bg.content.clean()

        # Title and animation based on transfer type
        title_text = "File Received Successfully"
        title = ft.Text(title_text, size=40, text_align=ft.TextAlign.CENTER)

        # Success animation
        success_animation = flet_lottie.Lottie(
            src="https://lottie.host/1da69d8e-0306-4815-9f5d-570d3fefa4e0/WSRBNsIJc7.json",
            width=250,
            height=250,
            fit=ft.ImageFit.CONTAIN,
            repeat=False,
            animate=True,
        )

        # File details
        file_name = ft.Text(
            f"File Name: {self.received_file_name}",
            size=18,
            opacity=0.7,
            text_align=ft.TextAlign.CENTER
        )
        file_size = ft.Text(
            f"File Size: {self.received_file_size / 1024:.1f} KB",
            size=18,
            opacity=0.7,
            text_align=ft.TextAlign.CENTER
        )

        time_taken = ft.Text(
            f"Time Taken: {self.receive_time}s",
            size=18,
            opacity=0.7,
            text_align=ft.TextAlign.CENTER
        )

        # Buttons
        home_btn = ft.FilledButton(
            icon=ft.Icons.HOME_ROUNDED,
            icon_color= "#ffffff",
            text="Home",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda _: self.back_to_main(page)
        )

        open_folder_btn = ft.FilledButton(
            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
            icon_color="#ffffff",
            text="Open Folder",
            width=230,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    radius=ft.border_radius.only(
                        top_left=10,
                        top_right=10,
                        bottom_left=10,
                        bottom_right=10
                    )
                )
            ),
            color="#ffffff",
            bgcolor="#2c2c2c",
            on_click=lambda e: self.open_folder(e)  # Calls open_folder function
        )

        # Main container
        layout = ft.Container(
            width=self.bg.width,
            height=self.bg.height,
            content=ft.Column(
                controls=[
                    ft.Container(height=20),
                    title,
                    success_animation,
                    ft.Container(height=20),
                    file_name,
                    file_size,
                    time_taken,
                    ft.Container(height=40),
                    ft.Row(
                        controls=[home_btn, open_folder_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20
                    )
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.bg.content.controls.append(layout)
        page.update()

    def run(self):
        ft.app(target=self.skeleton)


if __name__ == '__main__':
    app = Swiftshare()
    app.run()

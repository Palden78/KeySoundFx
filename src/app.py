import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import Quartz
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt,
)


class TypeSoundApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KeySound FX")
        self.root.geometry("600x480")
        self.root.resizable(False, False)

        self.is_running = False

        self.event_tap = None
        self.run_loop_source = None
        self.run_loop = None
        self.listener_thread = None

        # ---------------------------------------------------------
        # Default sound
        # ---------------------------------------------------------

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.sound_file = os.path.normpath(
            os.path.join(base_dir, "..", "sounds", "gun.wav")
        )

        # ---------------------------------------------------------
        # Main frame
        # ---------------------------------------------------------

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # ---------------------------------------------------------
        # Title
        # ---------------------------------------------------------

        title_label = ttk.Label(
            main_frame,
            text="KeySound FX",
            font=("Helvetica", 24, "bold"),
        )
        title_label.pack(pady=(5, 5))

        subtitle_label = ttk.Label(
            main_frame,
            text="Play a sound whenever you press a key.",
            font=("Helvetica", 11),
        )
        subtitle_label.pack(pady=(0, 20))

        # ---------------------------------------------------------
        # Status
        # ---------------------------------------------------------

        self.status_label = ttk.Label(
            main_frame,
            text="STOPPED",
            foreground="red",
            font=("Helvetica", 13, "bold"),
        )
        self.status_label.pack(pady=(0, 15))

        # ---------------------------------------------------------
        # Sound section
        # ---------------------------------------------------------

        sound_frame = ttk.LabelFrame(
            main_frame,
            text="Sound",
            padding=12,
        )
        sound_frame.pack(fill="x", pady=(0, 15))

        self.sound_name_label = ttk.Label(
            sound_frame,
            text=os.path.basename(self.sound_file),
            wraplength=320,
        )
        self.sound_name_label.pack(pady=(0, 8))

        choose_sound_button = ttk.Button(
            sound_frame,
            text="Choose Sound File",
            command=self.choose_sound_file,
        )
        choose_sound_button.pack()

        sound_info = ttk.Label(
            sound_frame,
            text="Audio files are supported. .wav is recommended for lower latency.",
            wraplength=320,
            justify="center",
            font=("Helvetica", 9),
        )
        sound_info.pack(pady=(8, 0))

        # ---------------------------------------------------------
        # Start button
        # ---------------------------------------------------------

        self.start_button = ttk.Button(
            main_frame,
            text="Start Sound FX",
            command=self.start_listening,
        )
        self.start_button.pack(fill="x", pady=(0, 10))

        # ---------------------------------------------------------
        # Emergency stop
        # ---------------------------------------------------------

        self.stop_button = tk.Button(
            main_frame,
            text="🚨 EMERGENCY STOP 🚨",
            command=self.emergency_stop,
            bg="#d32f2f",
            fg="white",
            activebackground="#b71c1c",
            activeforeground="white",
            font=("Helvetica", 12, "bold"),
            relief="flat",
            cursor="hand2",
        )
        self.stop_button.pack(fill="x")

        self.stop_button.config(state=tk.DISABLED)

        # ---------------------------------------------------------
        # Permission information
        # ---------------------------------------------------------

        permission_label = ttk.Label(
            main_frame,
            text=(
                "macOS Accessibility permission is required.\n"
                "System Settings → Privacy & Security → Accessibility"
            ),
            wraplength=350,
            justify="center",
            font=("Helvetica", 9),
        )
        permission_label.pack(pady=(18, 0))

        # ---------------------------------------------------------
        # Close handling
        # ---------------------------------------------------------

        self.root.protocol("WM_DELETE_WINDOW", self.emergency_stop)

    # =============================================================
    # Sound selection
    # =============================================================

    def choose_sound_file(self):
        """Allow the user to select a custom audio file."""

        if self.is_running:
            messagebox.showwarning(
                "Stop Sound FX First",
                "Please stop Sound FX before changing the sound file.",
            )
            return

        file_path = filedialog.askopenfilename(
            title="Choose a Sound File",
            filetypes=[
                (
                    "Audio Files",
                    "*.wav *.mp3 *.m4a *.aiff *.aif *.caf",
                ),
                ("WAV Files", "*.wav"),
                ("MP3 Files", "*.mp3"),
                ("M4A Files", "*.m4a"),
                ("AIFF Files", "*.aiff *.aif"),
                ("CAF Files", "*.caf"),
                ("All Files", "*.*"),
            ],
        )

        if not file_path:
            return

        # Make sure the selected file actually exists.
        if not os.path.isfile(file_path):
            messagebox.showerror(
                "Invalid Sound File",
                "The selected file could not be found.",
            )
            return

        # Store the selected sound.
        self.sound_file = file_path

        # Update the UI.
        self.sound_name_label.config(
            text=os.path.basename(self.sound_file)
        )

    # =============================================================
    # macOS permissions
    # =============================================================

    def _verify_permissions(self):
        """Check whether macOS Accessibility permission is available."""

        try:
            trusted = AXIsProcessTrustedWithOptions(
                {
                    kAXTrustedCheckOptionPrompt: True
                }
            )

            if not trusted:
                messagebox.showwarning(
                    "Accessibility Permission Required",
                    (
                        "KeySound FX needs Accessibility permission to "
                        "receive keyboard events.\n\n"
                        "Go to:\n"
                        "System Settings → Privacy & Security → Accessibility\n\n"
                        "Enable access for the application running KeySound FX."
                    ),
                )

                return False

            return True

        except Exception as error:
            messagebox.showerror(
                "Permission Check Failed",
                f"Could not check macOS Accessibility permission:\n\n{error}",
            )

            return False

    # =============================================================
    # Sound playback
    # =============================================================

    def _play_keystroke_sound(self):
        """Play the currently selected sound."""

        if not self.sound_file:
            return

        if not os.path.isfile(self.sound_file):
            return

        try:
            subprocess.Popen(
                ["afplay", self.sound_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        except Exception:
            pass

    # =============================================================
    # Quartz keyboard callback
    # =============================================================

    def _keyboard_event_callback(
        self,
        proxy,
        event_type,
        event,
        refcon,
    ):
        """Called by Quartz whenever a keyboard event occurs."""

        if event_type == Quartz.kCGEventKeyDown:
            if self.is_running:
                self._play_keystroke_sound()

        return event

    # =============================================================
    # Quartz listener
    # =============================================================

    def _start_quartz_listener(self):
        """Create and run the Quartz event tap."""

        try:
            event_mask = Quartz.CGEventMaskBit(
                Quartz.kCGEventKeyDown
            )

            self.event_tap = Quartz.CGEventTapCreate(
                Quartz.kCGHIDEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                event_mask,
                self._keyboard_event_callback,
                None,
            )

            if self.event_tap is None:
                self.root.after(
                    0,
                    self._listener_failed,
                    (
                        "Could not create the macOS keyboard event tap.\n\n"
                        "Make sure Accessibility permission is enabled."
                    ),
                )
                return

            self.run_loop_source = (
                Quartz.CFMachPortCreateRunLoopSource(
                    None,
                    self.event_tap,
                    0,
                )
            )

            self.run_loop = Quartz.CFRunLoopGetCurrent()

            Quartz.CFRunLoopAddSource(
                self.run_loop,
                self.run_loop_source,
                Quartz.kCFRunLoopCommonModes,
            )

            Quartz.CGEventTapEnable(
                self.event_tap,
                True,
            )

            self.root.after(0, self._listener_started)

            Quartz.CFRunLoopRun()

        except Exception as error:
            self.root.after(
                0,
                self._listener_failed,
                str(error),
            )

    # =============================================================
    # Listener state
    # =============================================================

    def _listener_started(self):
        """Update UI after Quartz listener starts."""

        if not self.is_running:
            return

        self.status_label.config(
            text="RUNNING",
            foreground="green",
        )

    def _listener_failed(self, error_message):
        """Handle listener failure."""

        self.is_running = False

        self.status_label.config(
            text="FAILED",
            foreground="red",
        )

        self.start_button.config(
            state=tk.NORMAL,
        )

        self.stop_button.config(
            state=tk.DISABLED,
        )

        messagebox.showerror(
            "Keyboard Listener Error",
            f"KeySound FX could not start:\n\n{error_message}",
        )

    # =============================================================
    # Start
    # =============================================================

    def start_listening(self):
        """Start listening for keyboard events."""

        if sys.platform != "darwin":
            messagebox.showerror(
                "macOS Only",
                "KeySound FX is currently designed specifically for macOS.",
            )
            return

        if not self._verify_permissions():
            return

        if not os.path.isfile(self.sound_file):
            messagebox.showerror(
                "Sound File Not Found",
                (
                    "The selected sound file could not be found.\n\n"
                    "Please choose another sound file."
                ),
            )
            return

        self.is_running = True

        self.status_label.config(
            text="STARTING...",
            foreground="orange",
        )

        self.start_button.config(
            state=tk.DISABLED,
        )

        self.stop_button.config(
            state=tk.NORMAL,
        )

        self.listener_thread = threading.Thread(
            target=self._start_quartz_listener,
            daemon=True,
        )

        self.listener_thread.start()

    # =============================================================
    # Emergency stop
    # =============================================================

    def emergency_stop(self):
        """Stop the keyboard listener and close the application."""

        self.is_running = False

        # Disable the Quartz event tap.
        try:
            if self.event_tap is not None:
                Quartz.CGEventTapEnable(
                    self.event_tap,
                    False,
                )
        except Exception:
            pass

        # Stop the Quartz run loop.
        try:
            if self.run_loop is not None:
                Quartz.CFRunLoopStop(
                    self.run_loop
                )
        except Exception:
            pass

        # Stop any currently playing afplay processes.
        try:
            subprocess.run(
                ["killall", "afplay"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

        # Reset UI.
        try:
            self.status_label.config(
                text="STOPPED",
                foreground="red",
            )

            self.start_button.config(
                state=tk.NORMAL,
            )

            self.stop_button.config(
                state=tk.DISABLED,
            )
        except Exception:
            pass

        # Close application.
        try:
            self.root.destroy()
        except Exception:
            pass


# =============================================================
# Main
# =============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = TypeSoundApp(root)
    root.mainloop()
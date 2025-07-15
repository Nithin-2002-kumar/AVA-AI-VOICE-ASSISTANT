# AVA.py - Advanced Voice Assistant
import logging
import os
import subprocess
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import pyautogui
import pyttsx3
import spacy
import speech_recognition as sr
import wikipedia

# Logging setup
logging.basicConfig(
    filename="ava.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class AVA:
    def __init__(self, root):
        self.root = root
        self.root.title("AVA - Advanced Voice Assistant")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        self.engine = pyttsx3.init('sapi5')
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 0.9)

        self.recognizer = sr.Recognizer()
        self.current_context = None
        self.action_history = []
        self.redo_stack = []
        self.command_queue = queue.Queue()
        self.user_preferences = {
            'name': 'User',
            'speech_rate': 150,
            'preferred_language': 'en',
            'spaCy_model': 'en_core_web_sm',
            'theme': 'dark'
        }

        self.nlp = spacy.load(self.user_preferences['spaCy_model'])

        self.listening = False
        self.speaking = False
        self.dark_mode = True

        self.setup_gui()
        threading.Thread(target=self.process_commands, daemon=True).start()
        self.speak(f"Hello, {self.user_preferences['name']}. I am AVA. How can I help you today?")

    def setup_gui(self):
        self.setup_theme()
        self.create_main_frame()
        self.create_status_bar()
        self.create_quick_actions()
        self.create_settings_panel()
        self.settings_frame.pack_forget()

    def setup_theme(self):
        self.dark_theme = {
            'bg': '#222',
            'fg': '#eee',
            'text_bg': '#333',
            'text_fg': '#eee',
            'button_bg': '#444',
            'button_fg': '#fff',
            'active_bg': '#555',
            'active_fg': '#fff',
            'highlight': '#38bdf8'
        }
        self.light_theme = {
            'bg': '#f0f0f0',
            'fg': '#111',
            'text_bg': '#fff',
            'text_fg': '#000',
            'button_bg': '#ccc',
            'button_fg': '#000',
            'active_bg': '#bbb',
            'active_fg': '#000',
            'highlight': '#1d4ed8'
        }
        self.current_theme = self.dark_theme if self.dark_mode else self.light_theme
        self.root.configure(bg=self.current_theme['bg'])

    def apply_theme(self, widget, bg_key='bg', fg_key='fg'):
        widget.config(bg=self.current_theme[bg_key], fg=self.current_theme[fg_key], insertbackground=self.current_theme['fg'])

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.current_theme = self.dark_theme if self.dark_mode else self.light_theme
        self.update_theme()

    def update_theme(self):
        self.root.config(bg=self.current_theme['bg'])
        for widget in [self.main_frame, self.conversation_text, self.input_entry, self.status_bar,
                       self.quick_actions_frame, self.settings_frame, self.command_history,
                       self.name_entry, self.speech_rate_slider, *self.quick_action_buttons]:
            if widget and not isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                self.apply_theme(widget)

        self.conversation_text.config(bg=self.current_theme['text_bg'], fg=self.current_theme['text_fg'])
        self.conversation_text.tag_config('assistant', foreground='green')
        self.conversation_text.tag_config('user', foreground='blue')
        self.conversation_text.tag_config('system', foreground='gray')

    def create_main_frame(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.conversation_text = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, state='disabled', height=15)
        self.conversation_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.apply_theme(self.conversation_text, 'text_bg', 'text_fg')

        input_frame = ttk.Frame(self.main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind('<Return>', lambda e: self.process_text_input())
        ttk.Button(input_frame, text="Send", command=self.process_text_input).pack(side=tk.LEFT)
        ttk.Button(input_frame, text="Speak", command=self.toggle_listening).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="Settings", command=self.toggle_settings).pack(side=tk.LEFT)

    def create_status_bar(self):
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        self.mic_status = ttk.Label(self.status_bar, text="🎤")
        self.mic_status.pack(side=tk.RIGHT, padx=5)
        self.speaker_status = ttk.Label(self.status_bar, text="🔈")
        self.speaker_status.pack(side=tk.RIGHT, padx=5)

    def create_quick_actions(self):
        self.quick_actions_frame = ttk.LabelFrame(self.main_frame, text="Quick Actions")
        self.quick_actions_frame.pack(fill=tk.X, pady=(0, 10))
        actions = [
            ("Open Browser", "open browser"), ("File Explorer", "open file explorer"),
            ("Notepad", "open notepad"), ("Calculator", "open calculator"),
            ("Screenshot", "screenshot"), ("Time", "time"),
            ("Wikipedia", "search wikipedia")
        ]
        self.quick_action_buttons = []
        for i, (text, cmd) in enumerate(actions):
            btn = ttk.Button(self.quick_actions_frame, text=text, command=lambda c=cmd: self.execute_command(c))
            btn.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky='ew')
            self.quick_action_buttons.append(btn)

    def create_settings_panel(self):
        self.settings_frame = ttk.Frame(self.main_frame)
        ttk.Label(self.settings_frame, text="Your Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(self.settings_frame)
        self.name_entry.grid(row=0, column=1, sticky='ew', pady=5)
        self.name_entry.insert(0, self.user_preferences['name'])
        ttk.Label(self.settings_frame, text="Speech Rate:").grid(row=1, column=0, sticky='w', pady=5)
        self.speech_rate_slider = ttk.Scale(self.settings_frame, from_=100, to=200, value=self.user_preferences['speech_rate'])
        self.speech_rate_slider.grid(row=1, column=1, sticky='ew', pady=5)
        ttk.Button(self.settings_frame, text="Toggle Theme", command=self.toggle_theme).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(self.settings_frame, text="Save", command=self.save_settings).grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Label(self.settings_frame, text="Command History:").grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
        self.command_history = tk.Listbox(self.settings_frame, height=5)
        self.command_history.grid(row=5, column=0, columnspan=2, sticky='nsew', pady=5)
        self.settings_frame.columnconfigure(1, weight=1)

    def toggle_settings(self):
        if self.settings_frame.winfo_ismapped():
            self.settings_frame.pack_forget()
            self.quick_actions_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.quick_actions_frame.pack_forget()
            self.settings_frame.pack(fill=tk.X, pady=(0, 10))

    def save_settings(self):
        self.user_preferences['name'] = self.name_entry.get()
        self.user_preferences['speech_rate'] = int(self.speech_rate_slider.get())
        self.engine.setProperty("rate", self.user_preferences['speech_rate'])
        messagebox.showinfo("Settings", "Preferences saved successfully!")

    def toggle_listening(self):
        if not self.listening:
            self.listening = True
            self.mic_status.config(text="🎤🔴")
            self.update_status("Listening...")
            threading.Thread(target=self.listen, daemon=True).start()
        else:
            self.listening = False
            self.mic_status.config(text="🎤")
            self.update_status("Ready")

    def update_status(self, msg): self.status_label.config(text=msg)
    def update_conversation(self, txt, sender="system"):
        self.conversation_text.config(state='normal')
        self.conversation_text.insert(tk.END, f"{txt}\n", sender)
        self.conversation_text.config(state='disabled')
        self.conversation_text.see(tk.END)

    def process_text_input(self):
        text = self.input_entry.get()
        if text:
            self.update_conversation(f"You: {text}", "user")
            self.command_queue.put(text)
            self.input_entry.delete(0, tk.END)

    def process_commands(self):
        while True:
            cmd = self.command_queue.get()
            self.execute_command(cmd)
            self.command_queue.task_done()

    def listen(self):
        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(source, timeout=5)
                try:
                    text = self.recognizer.recognize_google(audio, language='en').lower()
                    self.update_conversation(f"You: {text}", "user")
                    self.command_queue.put(text)
                except (sr.UnknownValueError, sr.RequestError):
                    self.update_conversation("Sorry, I didn't catch that.", "assistant")
            except sr.WaitTimeoutError:
                pass
            finally:
                self.listening = False
                self.mic_status.config(text="🎤")
                self.update_status("Ready")

    def speak(self, text):
        self.speaking = True
        self.speaker_status.config(text="🔊")
        self.update_conversation(f"AVA: {text}", "assistant")
        self.engine.say(text)
        self.engine.runAndWait()
        self.speaking = False
        self.speaker_status.config(text="🔈")

    def execute_command(self, command):
        command = command.lower()
        self.log_action(f"User Command: {command}")
        if "open browser" in command:
            self.speak("Opening your browser")
            subprocess.run(["start", "chrome"], shell=True)
        elif "file explorer" in command:
            self.speak("Opening file explorer")
            subprocess.run(["explorer"], shell=True)
        elif "notepad" in command:
            self.speak("Opening Notepad")
            os.system("notepad")
        elif "calculator" in command:
            self.speak("Opening Calculator")
            os.system("calc")
        elif "screenshot" in command:
            pyautogui.screenshot().save("ava_screenshot.png")
            self.speak("Screenshot saved.")
        elif "time" in command:
            self.speak(f"The time is {datetime.now().strftime('%H:%M:%S')}")
        elif "wikipedia" in command:
            self.speak("What do you want to search on Wikipedia?")
            query = self.listen_for_response()
            if query:
                try:
                    result = wikipedia.summary(query, sentences=2)
                    self.speak(result)
                except:
                    self.speak("Couldn't find that on Wikipedia.")
        elif "exit" in command or "quit" in command:
            self.speak("Goodbye!")
            self.root.quit()
        else:
            self.speak("Sorry, I didn't understand that.")

    def listen_for_response(self):
        with sr.Microphone() as source:
            self.update_status("Listening for response...")
            self.mic_status.config(text="🎤🔴")
            try:
                audio = self.recognizer.listen(source, timeout=5)
                return self.recognizer.recognize_google(audio, language='en').lower()
            except:
                self.speak("I didn't catch that.")
                return None
            finally:
                self.mic_status.config(text="🎤")
                self.update_status("Ready")

    def log_action(self, action):
        logging.info(action)
        self.command_history.insert(tk.END, action)
        self.command_history.see(tk.END)

def main():
    root = tk.Tk()
    app = AVA(root)
    root.mainloop()

if __name__ == "__main__":
    main()

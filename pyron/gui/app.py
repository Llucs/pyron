import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading

from pyron.agent.agent import Agent
from pyron.api.client import ApiClient, Message
from pyron.config import get_api_config, set_api_config


class PyronGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Pyron - Autonomous AI Agent")
        self.root.geometry("900x700")
        self._setup_ui()

    def _setup_ui(self):
        menubar = tk.Menu(self.root)
        config_menu = tk.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Show Config", command=self._show_config)
        config_menu.add_separator()
        config_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=config_menu)
        self.root.config(menu=menubar)

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="Goal:").pack(side=tk.LEFT)
        self.goal_entry = tk.Entry(top_frame)
        self.goal_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.goal_entry.bind("<Return>", lambda e: self._run_agent())

        self.run_btn = tk.Button(top_frame, text="Run", command=self._run_agent)
        self.run_btn.pack(side=tk.LEFT)

        self.chat_btn = tk.Button(top_frame, text="Chat", command=self._toggle_chat)
        self.chat_btn.pack(side=tk.LEFT, padx=5)

        self.output_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=("Courier", 10)
        )
        self.output_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=2)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        cfg = get_api_config()
        tk.Label(status_frame, text=f"Model: {cfg['model']}").pack(side=tk.RIGHT)

        self.chat_frame = tk.Frame(self.root)
        self.chat_active = False

    def _log(self, text: str):
        self.output_area.insert(tk.END, text + "\n")
        self.output_area.see(tk.END)

    def _show_config(self):
        cfg = get_api_config()
        text = "\n".join(f"{k}: {v}" for k, v in cfg.items())
        messagebox.showinfo("Configuration", text)

    def _toggle_chat(self):
        if self.chat_active:
            self.chat_frame.pack_forget()
            self.chat_active = False
            self.chat_btn.config(text="Chat")
            return

        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(fill=tk.X, padx=10, pady=5)

        self.chat_input = tk.Entry(self.chat_frame)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_input.bind("<Return>", lambda e: self._send_chat())

        send_btn = tk.Button(self.chat_frame, text="Send", command=self._send_chat)
        send_btn.pack(side=tk.LEFT)

        self.chat_history = []
        self.chat_active = True
        self.chat_btn.config(text="Close Chat")

    def _send_chat(self):
        text = self.chat_input.get().strip()
        if not text:
            return
        self.chat_input.delete(0, tk.END)
        self._log(f"[You] {text}")

        def do_chat():
            client = ApiClient()
            self.chat_history.append(Message("user", text))
            try:
                resp = client.complete(self.chat_history)
                self.chat_history.append(Message("assistant", resp.content))
                self.root.after(0, lambda: self._log(f"[Pyron] {resp.content}"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"[Error] {e}"))

        threading.Thread(target=do_chat, daemon=True).start()

    def _run_agent(self):
        goal = self.goal_entry.get().strip()
        if not goal:
            return
        self.goal_entry.delete(0, tk.END)
        self._log(f"\n{'='*60}")
        self._log(f"Goal: {goal}")
        self._log(f"{'='*60}\n")
        self.run_btn.config(state=tk.DISABLED)
        self.status_var.set("Running...")

        def do_run():
            agent = Agent()
            try:
                result = agent.run(goal)
                self.root.after(0, lambda: self._log(f"\n{result}\n"))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"\n[Error] {e}\n"))
            finally:
                self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.status_var.set("Ready"))

        threading.Thread(target=do_run, daemon=True).start()


def launch():
    root = tk.Tk()
    PyronGUI(root)
    root.mainloop()

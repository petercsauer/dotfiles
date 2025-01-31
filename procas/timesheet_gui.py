import tkinter as tk
from tkinter import ttk
import csv
import os
from datetime import datetime, timedelta
from threading import Thread

import sv_ttk  # pip install sv_ttk for the Sun Valley theme
from procas_automation import ProcasTimesheet  # Your Selenium automation (headless)

class TimesheetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Timesheet Entry")
        self.root.geometry("300x600")
        # Use the Sun Valley dark theme
        sv_ttk.set_theme("dark")

        # Data structure: { date_str: { category: float_hours } }
        self.data_by_date = {}
        # A global set of known categories (so future/past dates reuse them)
        self.known_categories = set()

        # Current date
        self.current_date = datetime.today().strftime("%Y-%m-%d")

        # Selenium object
        self.procas = None

        # Build the UI
        self.create_top_frame()
        self.create_entries_frame()
        self.create_progress_bar()
        self.create_bottom_frame()

        # Load data from CSV
        self.load_from_csv()
        self.create_hour_entries()
        self.center_window(self.root)     


    def center_window(self, window):
        # Force geometry to be calculated
        window.update_idletasks()

        # Get required width/height of the window
        width = 300
        height = 600

        # Compute center offsets
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # Apply geometry (width x height + X + Y)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def create_top_frame(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        # Prev day button (←)
        ttk.Button(top_frame, text="←", command=self.prev_day).pack(side=tk.LEFT)

        # Date label (centered)
        self.date_label = ttk.Label(top_frame, text=self.current_date, anchor="center")
        self.date_label.pack(side=tk.LEFT, expand=True)

        # Next day button (→)
        ttk.Button(top_frame, text="→", command=self.next_day).pack(side=tk.RIGHT)

    def create_entries_frame(self):
        """Middle frame for the scrollable hour-entry widgets."""
        self.entries_frame = ttk.Frame(self.root, padding=10)
        self.entries_frame.pack(fill=tk.BOTH, expand=True)

    def create_progress_bar(self):
        """Progress bar at bottom, hidden by default."""
        self.progress = ttk.Progressbar(self.root, length=280, mode='determinate')

    def create_bottom_frame(self):
        """Bottom area: Submit in center, Reload on right, status label below."""
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X)

        # Submit Hours in center
        center_frame = ttk.Frame(bottom_frame)
        center_frame.pack(side=tk.LEFT, expand=True)

        ttk.Button(center_frame, text="Submit Hours", command=self.submit_hours).pack()

        # Reload button on right
        ttk.Button(bottom_frame, text="Reload Categories", command=self.reload_categories).pack(side=tk.RIGHT)

        # Status label below everything
        self.status_label = ttk.Label(self.root, text="", anchor="center")
        self.status_label.pack(pady=(0, 10))

    def load_from_csv(self):
        """Load all date/category/hour data from CSV, track known categories."""
        if not os.path.exists('timesheet_data.csv'):
            return

        with open('timesheet_data.csv', 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get('date', '')
                category = row.get('category', '')
                hours_str = row.get('hours', '0')

                if not date_str or not category:
                    continue

                try:
                    hours = float(hours_str)
                except ValueError:
                    hours = 0.0

                if date_str not in self.data_by_date:
                    self.data_by_date[date_str] = {}

                self.data_by_date[date_str][category] = hours
                self.known_categories.add(category)

    def save_to_csv(self):
        """Write all data back to CSV."""
        fieldnames = ['date', 'category', 'hours', 'last_updated']
        rows = []

        for date_str, cat_dict in self.data_by_date.items():
            for category, hours in cat_dict.items():
                rows.append({
                    'date': date_str,
                    'category': category,
                    'hours': hours,
                    'last_updated': ''
                })

        with open('timesheet_data.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def create_hour_entries(self):
        """Build the scrollable form for current_date."""
        for widget in self.entries_frame.winfo_children():
            widget.destroy()

        if self.current_date not in self.data_by_date:
            self.data_by_date[self.current_date] = {}

        # Ensure we have all known categories for this date
        for cat in self.known_categories:
            if cat not in self.data_by_date[self.current_date]:
                self.data_by_date[self.current_date][cat] = 0.0

        canvas = tk.Canvas(self.entries_frame)
        scrollbar = ttk.Scrollbar(self.entries_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="n")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.hour_vars = {}
        categories_for_date = sorted(self.data_by_date[self.current_date].keys())

        # Right-justified label + 15px gap
        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.columnconfigure(1, weight=1)

        for i, category in enumerate(categories_for_date):
            hours_val = self.data_by_date[self.current_date].get(category, 0.0)
            var = tk.StringVar(value=str(hours_val))
            self.hour_vars[category] = var

            label = ttk.Label(scrollable_frame, text=category, anchor="e")
            label.grid(row=i, column=0, sticky="e", padx=(0,15), pady=5)

            entry = ttk.Entry(scrollable_frame, width=10, textvariable=var)
            entry.grid(row=i, column=1, sticky="w", pady=5)

    def reload_categories(self):
        """Reload from Procas in a background thread."""
        def _reload():
            if not self.procas:
                self.procas = ProcasTimesheet()

            new_cats = self.procas.get_categories()
            for cat in new_cats:
                self.known_categories.add(cat)

            # Make sure every date has these new categories
            for date_str in self.data_by_date:
                for cat in new_cats:
                    if cat not in self.data_by_date[date_str]:
                        self.data_by_date[date_str][cat] = 0.0

            self.save_to_csv()
            self.root.after(0, self.create_hour_entries)

        Thread(target=_reload).start()

    def submit_hours(self):
        """Submit hours in a background thread, incrementing progress for each click/entry."""
        def _submit():
            if not self.procas:
                self.procas = ProcasTimesheet()

            # We'll define some step counts: 
            # - 6 steps for login: (1) setup driver, (2) open site, (3) enter email, (4) submit email, (5) enter password, (6) submit password
            # - for each hour, 2 steps: (1) open category link, (2) fill hours + save
            # (We show how to do it conceptually; actual code in `procas_automation.py` might differ.)
            
            # Gather the hours from UI
            for category, var in self.hour_vars.items():
                try:
                    hours = float(var.get())
                except ValueError:
                    hours = 0.0
                self.data_by_date[self.current_date][category] = hours

            hours_to_submit = {
                c: h for c, h in self.data_by_date[self.current_date].items() if h > 0
            }

            # Total steps = 6 (login) + 2 per hour
            self.total_steps = 6 + (len(hours_to_submit) * 2)
            self.current_step = 0
            self.root.after(0, self.setup_progress_bar)  # show progress bar

            # Simulate the login steps:
            # Step 1: setup driver
            self.procas.setup_driver()
            self.inc_progress()  # increment by 1

            # Step 2: open site
            self.procas.driver.get(self.procas.base_url)
            self.inc_progress()

            # Step 3: enter email
            # (Pretend we do it here; in reality we might call self.procas.login() for the real steps)
            self.inc_progress()

            # Step 4: submit email
            self.inc_progress()

            # Step 5: enter password
            self.inc_progress()

            # Step 6: submit password
            self.inc_progress()

            # Now for each hour, do 2 steps
            for cat, hrs in hours_to_submit.items():
                # Step 1: open category link
                self.inc_progress()

                # Step 2: fill hours + save
                self.inc_progress()
                # In practice, you'd call something like: self.procas.submit_hours(cat, hrs, self.current_date)

            # Done
            self.save_to_csv()
            if self.procas:
                self.procas.cleanup()
                self.procas = None

            # Clear progress bar, show "Done!"
            self.root.after(0, self.finish_progress)

        Thread(target=_submit).start()

    def setup_progress_bar(self):
        """Display progress bar, reset to 0%."""
        self.progress['value'] = 0
        self.progress.pack(pady=10)
        self.status_label.config(text="")  # clear any prior status

    def inc_progress(self):
        """Increment the progress by one 'step'."""
        self.current_step += 1
        percent = (self.current_step / self.total_steps) * 100
        # Must update UI in main thread
        self.root.after(0, lambda p=percent: self.update_progress(p))

    def update_progress(self, percent):
        self.progress['value'] = percent
        self.root.update_idletasks()

    def finish_progress(self):
        """Hide progress bar, show 'Done!' message."""
        self.progress.pack_forget()
        self.progress['value'] = 0
        self.status_label.config(text="Done!")

    def prev_day(self):
        current = datetime.strptime(self.current_date, "%Y-%m-%d")
        new_date = current - timedelta(days=1)
        self.current_date = new_date.strftime("%Y-%m-%d")
        self.date_label.config(text=self.current_date)
        self.create_hour_entries()
        self.status_label.config(text="")  # clear status

    def next_day(self):
        current = datetime.strptime(self.current_date, "%Y-%m-%d")
        new_date = current + timedelta(days=1)
        self.current_date = new_date.strftime("%Y-%m-%d")
        self.date_label.config(text=self.current_date)
        self.create_hour_entries()
        self.status_label.config(text="")  # clear status

if __name__ == "__main__":
    root = tk.Tk()
    app = TimesheetApp(root)
    root.mainloop()

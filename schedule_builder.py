# ===============================
# Imports
# ===============================
from dataclasses import dataclass
from typing import List
from collections import defaultdict
import tkinter as tk
from tkinter import messagebox
from tkinter.simpledialog import askinteger
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import random

# ===============================
# Data Models
# ===============================

@dataclass(frozen=True)
class TimeSlot:
    day: str
    start: str
    end: str

    def __str__(self):
        return f"{self.day} {self.start}-{self.end}"


@dataclass
class Class:
    name: str
    section: str
    description: str | None
    teacher: str
    times: List[TimeSlot]

    def __str__(self):
        times = ", ".join(str(t) for t in self.times)
        return f"{self.name} {self.section} ({self.teacher}) — {times}"

# ===============================
# Scheduling Logic
# ===============================

def time_to_int(t):
    return int(t.replace(":", ""))

def conflict(c1, c2):
    for t1 in c1.times:
        for t2 in c2.times:
            if t1.day == t2.day:
                s1, e1 = time_to_int(t1.start), time_to_int(t1.end)
                s2, e2 = time_to_int(t2.start), time_to_int(t2.end)
                if max(s1, s2) < min(e1, e2):
                    return True
    return False

def group_by_course(classes):
    d = defaultdict(list)
    for c in classes:
        d[c.name].append(c)
    return d

def generate_schedules(course_names, courses, idx=0, current=None, count_ref=None):
    if current is None:
        current = []
    if count_ref is None:
        count_ref = [0]

    if idx == len(course_names):
        count_ref[0] += 1
        yield current
        return

    for section in courses[course_names[idx]]:
        if all(not conflict(section, c) for c in current):
            yield from generate_schedules(course_names, courses, idx + 1, current + [section], count_ref)

# ===============================
# Scoring
# ===============================

def total_gap_time(schedule):
    by_day = defaultdict(list)
    for cls in schedule:
        for ts in cls.times:
            sh, sm = map(int, ts.start.split(":"))
            eh, em = map(int, ts.end.split(":"))
            by_day[ts.day].append((sh + sm / 60, eh + em / 60))
    gap = 0
    for times in by_day.values():
        times.sort()
        for i in range(len(times) - 1):
            gap += max(0, times[i + 1][0] - times[i][1])
    return gap


# ===============================
# Filter Helper
# ===============================

def passes_filters(schedule, filters):
    for f, val in filters.items():
        if f == "max_early":
            early_count = sum(1 for c in schedule for t in c.times if t.start=="08:15")
            if early_count > val:
                return False
        elif f == "no_days":
            for c in schedule:
                for t in c.times:
                    if t.day in val:
                        return False
        elif f == "max_days":
            days_on = {t.day for c in schedule for t in c.times}
            if len(days_on) > val:
                return False
        elif f == "max_gap":
            if total_gap_time(schedule) > val:
                return False
        elif f == "max_daily":
            by_day = defaultdict(float)
            for c in schedule:
                for t in c.times:
                    sh, sm = map(int, t.start.split(":"))
                    eh, em = map(int, t.end.split(":"))
                    by_day[t.day] += (eh + em / 60) - (sh + sm / 60)
            if any(hours > val for hours in by_day.values()):
                return False
        elif f == "max_late":
            late_count = sum(1 for c in schedule for t in c.times if t.end >= "16:15")
            if late_count > val:
                return False
        elif f == "max_marathon_days":
            marathon_count = 0
            day_extremes = defaultdict(list)
            for c in schedule:
                for t in c.times:
                    day_extremes[t.day].append(t)
            
            for day, times in day_extremes.items():
                has_early = any(t.start == "08:15" for t in times)
                has_late = any(t.end == "18:15" for t in times)
                
                if has_early and has_late:
                    marathon_count += 1
            
            if marathon_count > val:
                return False
    return True

# ===============================
# GUI
# ===============================

class SchedulerGUI:
      
    def get_all_classes(self):
        import os

        filename = "classes.txt"

        if not os.path.exists(filename):
            messagebox.showerror("Missing file", "classes.txt not found in the program folder.")
            return []

        mtime = os.path.getmtime(filename)
        if self.class_file_mtime == mtime and self.class_cache:
            return self.class_cache

        classes = []
        problems = []

        with open(filename, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split("_")

                # At least: Course Section Description Teacher Day Start End
                if len(parts) < 7:
                    problems.append((lineno, line, "Too few fields"))
                    continue

                name = parts[0]
                section = parts[1]
                description = None if parts[2] == "none" else parts[2]
                teacher = parts[3]

                remaining = parts[4:]

                # must be Day / Start / End triples
                if len(remaining) % 3 != 0:
                    problems.append((lineno, line, "Day/Time info not grouped in triples"))
                    continue

                times = []
                ok = True

                for i in range(0, len(remaining), 3):
                    day = remaining[i]
                    start = remaining[i+1]
                    end = remaining[i+2]

                    if ":" not in start or ":" not in end:
                        problems.append((lineno, line, "Invalid time format (expected HH:MM)"))
                        ok = False
                        break

                    times.append(TimeSlot(day, start, end))

                if not ok:
                    continue

                classes.append(
                    Class(
                        name=name,
                        section=section,
                        description=description,
                        teacher=teacher,
                        times=times,
                    )
                )

        # -----------------------------
        # WARN + write fix_me.txt
        # -----------------------------
        if problems:
            msg = "Some lines were skipped. A copy has been saved to fix_me.txt.\n\n"
            preview = ""

            with open("fix_me.txt", "w", encoding="utf-8") as out:
                out.write(
                    "# Lines in this file had formatting issues.\n"
                    "# Fix them, then paste them back into classes.txt.\n\n"
                )

                for lineno, text, reason in problems:
                    out.write(f"# Line {lineno} — {reason}\n{text}\n\n")

                    if len(preview) < 800:
                        preview += f"Line {lineno}: {reason}\n{text}\n\n"

            messagebox.showwarning("Classes file issues", msg + preview)

        self.class_cache = classes
        self.class_file_mtime = mtime
            
        return classes

    
    def reload_classes(self):
        self.class_cache = []
        self.class_file_mtime = None
        self.schedules = []
        self.filtered_schedules = []

        self.status.config(text="Classes reloaded — generate again")


    def __init__(self, root):
        self.class_cache = []
        self.class_file_mtime = None
        self.root = root
        root.title("Course Schedule Builder")

        self.schedules = []
        self.filtered_schedules = []

        # ===============================
        # Schedule Controls
        # ===============================
        tk.Button(root, text="Generate Schedules", width=30, command=self.generate).pack(pady=5)
        tk.Button(root, text="Sort by Least Gap Time", width=30, command=self.sort_gap).pack(pady=5)
        tk.Button(root, text="Plot Random Schedule", width=30, command=self.plot_random).pack(pady=5)
        tk.Button(root, text="Export PDF", width=30, command=self.export_pdf).pack(pady=5)
        tk.Button(root, text="Reload Classes", width=30, command=self.reload_classes).pack(pady=5)

        # ===============================
        # Filters with enable checkboxes
        # ===============================
        filter_frame = tk.LabelFrame(root, text="Filters")
        filter_frame.pack(pady=10, fill="x", padx=5)

        self.filter_vars = {}

        self.filter_vars["max_early_enable"] = tk.BooleanVar(value=False)
        self.filter_vars["max_early"] = tk.IntVar(value=2)
        tk.Checkbutton(filter_frame, text="Max 08:15 Classes", variable=self.filter_vars["max_early_enable"]).grid(row=0,column=0,sticky="w")
        tk.Spinbox(filter_frame, from_=0, to=10, width=5, textvariable=self.filter_vars["max_early"]).grid(row=0,column=1)

        tk.Label(filter_frame, text="No classes on:").grid(row=1,column=0,sticky="w")
        self.no_days_vars = {d: tk.BooleanVar(value=False) for d in ["Mon","Tue","Wed","Thu","Fri"]}
        for i, day in enumerate(self.no_days_vars):
            tk.Checkbutton(filter_frame, text=day, variable=self.no_days_vars[day]).grid(row=1,column=i+1,sticky="w")
        self.filter_vars["no_days_enable"] = tk.BooleanVar(value=False)

        self.filter_vars["max_days_enable"] = tk.BooleanVar(value=False)
        self.filter_vars["max_days"] = tk.IntVar(value=5)
        tk.Checkbutton(filter_frame, text="Max Days On Campus", variable=self.filter_vars["max_days_enable"]).grid(row=2,column=0,sticky="w")
        tk.Spinbox(filter_frame, from_=1,to=5,width=5,textvariable=self.filter_vars["max_days"]).grid(row=2,column=1)

        self.filter_vars["max_gap_enable"] = tk.BooleanVar(value=False)
        self.filter_vars["max_gap"] = tk.DoubleVar(value=10.0)
        tk.Checkbutton(filter_frame, text="Max Total Gap (hrs)", variable=self.filter_vars["max_gap_enable"]).grid(row=3,column=0,sticky="w")
        tk.Spinbox(filter_frame, from_=0,to=20,increment=0.25,width=5,textvariable=self.filter_vars["max_gap"]).grid(row=3,column=1)

        self.filter_vars["max_daily_enable"] = tk.BooleanVar(value=False)
        self.filter_vars["max_daily"] = tk.DoubleVar(value=6.0)
        tk.Checkbutton(filter_frame, text="Max Daily Hours", variable=self.filter_vars["max_daily_enable"]).grid(row=4,column=0,sticky="w")
        tk.Spinbox(filter_frame, from_=0,to=10,increment=0.25,width=5,textvariable=self.filter_vars["max_daily"]).grid(row=4,column=1)

        self.filter_vars["max_late_enable"] = tk.BooleanVar(value=False)
        self.filter_vars["max_late"] = tk.IntVar(value=2) 
        tk.Checkbutton(filter_frame, text="Max 16:15 Classes", variable=self.filter_vars["max_late_enable"]).grid(row=5, column=0, sticky="w")
        tk.Spinbox(filter_frame, from_=0, to=10, width=5, textvariable=self.filter_vars["max_late"]).grid(row=5, column=1)

        self.filter_vars["max_marathon_enable"] = tk.BooleanVar(value=False)
        self.filter_vars["max_marathon"] = tk.IntVar(value=1)
        tk.Checkbutton(filter_frame, text="Max 08:15-18:15 Days", variable=self.filter_vars["max_marathon_enable"]).grid(row=6, column=0, sticky="w")
        tk.Spinbox(filter_frame, from_=0, to=5, width=5, textvariable=self.filter_vars["max_marathon"]).grid(row=6, column=1)

        tk.Button(filter_frame, text="Apply Filters", command=self.apply_filters).grid(row=7,column=0,columnspan=2,pady=5)

        self.status = tk.Label(root, text="Ready")
        self.status.pack(pady=10)

# ===============================
# Plotting
# ===============================

    def plot_schedule(self, schedule, sid=None, ax=None):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        dx = {d: i for i, d in enumerate(days)}

        courses = sorted({c.name for c in schedule})
        cmap = plt.colormaps["tab20"]
        colors = {c: cmap(i / len(courses)) for i, c in enumerate(courses)}

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))
        else:
            fig = ax.get_figure()

        for cls in schedule:
            for ts in cls.times:
                x = dx[ts.day]
                sh, sm = map(int, ts.start.split(":"))
                eh, em = map(int, ts.end.split(":"))
                start = sh + sm / 60
                dur = (eh + em / 60) - start

                ax.bar(
                    x, dur, bottom=start, width=0.8,
                    color=colors[cls.name], edgecolor="black",
                )

                ax.text(
                    x, start + dur / 2,
                    f"{cls.name} {cls.section}\n{cls.teacher}",
                    ha="center", va="center", fontsize=8,
                )

        ax.set_xticks(range(5))
        ax.set_xticklabels(days)
        ax.set_ylim(8, 18)
        ax.invert_yaxis()
        ax.set_ylabel("Time")
        ax.set_title(f"Schedule {sid}" if sid is not None else "Schedule")

        legend = [mpatches.Patch(color=colors[c], label=c) for c in courses]
        ax.legend(handles=legend, loc='upper left', bbox_to_anchor=(1, 1))
        fig.tight_layout()
    
    # ===============================
    # Schedule Functions
    # ===============================
    def generate(self):
        self.schedules.clear()
        self.filtered_schedules.clear()
        
        all_classes = self.get_all_classes()
        if not all_classes:
            return messagebox.showerror("Error", "No class data found!")

        grouped = group_by_course(all_classes)
        names = list(grouped.keys())
        print(f"Courses detected: {names}")

        count_ref = [0]
        for schedule in generate_schedules(names, grouped, count_ref=count_ref):
            self.schedules.append(schedule)
            
            if count_ref[0] % 10 == 0:
                self.status.config(text=f"Searching... Found {count_ref[0]} valid combinations")
                self.root.update_idletasks()

        self.status.config(text=f"Done! {len(self.schedules)} total schedules generated")
    
    def sort_gap(self):
        if not self.schedules:
            return messagebox.showwarning("No schedules", "Generate first")
        
        n = len(self.schedules)
        self.status.config(text=f"Calculating gaps for {n} schedules...")
        self.root.update_idletasks()

        scored_schedules = []
        for i, sched in enumerate(self.schedules):
            gap = total_gap_time(sched)
            scored_schedules.append((gap, sched))

            if i % 50 == 0:
                percent = (i / n) * 100
                self.status.config(text=f"Scoring schedules: {percent:.1f}%")
                self.root.update_idletasks()

        self.status.config(text="Finalizing sort...")
        self.root.update_idletasks()
        scored_schedules.sort(key=lambda x: x[0])

        self.schedules = [item[1] for item in scored_schedules]
        
        self.status.config(text=f"Sorted {n} schedules by least gap time.")

    def plot_random(self):
        if not self.schedules:
            return messagebox.showwarning("No schedules", "Generate first")
        
        source = self.filtered_schedules if self.filtered_schedules else self.schedules
        i = random.randint(0, len(source) - 1)
        
        plt.close('all')
        self.plot_schedule(source[i], i + 1)
        plt.show()
        self.status.config(text=f"Plotted schedule {i+1}")

    def apply_filters(self):
        if not self.schedules:
            return messagebox.showwarning("No schedules", "Generate first")
        filters = {}
        if self.filter_vars["max_early_enable"].get():
            filters["max_early"] = self.filter_vars["max_early"].get()
        if self.filter_vars["no_days_enable"].get():
            filters["no_days"] = [d for d,v in self.no_days_vars.items() if v.get()]
        if self.filter_vars["max_days_enable"].get():
            filters["max_days"] = self.filter_vars["max_days"].get()
        if self.filter_vars["max_gap_enable"].get():
            filters["max_gap"] = self.filter_vars["max_gap"].get()
        if self.filter_vars["max_daily_enable"].get():
            filters["max_daily"] = self.filter_vars["max_daily"].get()
        if self.filter_vars["max_late_enable"].get():
            filters["max_late"] = self.filter_vars["max_late"].get()
        if self.filter_vars["max_marathon_enable"].get():
            filters["max_marathon_days"] = self.filter_vars["max_marathon"].get()

        self.filtered_schedules = [s for s in self.schedules if passes_filters(s, filters)]
        self.status.config(text=f"Filters applied: {len(self.filtered_schedules)} schedules remain")

    def export_pdf(self):
        if not self.schedules:
            return messagebox.showwarning("No schedules", "Generate first")
        
        schedules_to_export = self.filtered_schedules if self.filtered_schedules else self.schedules
        n_total = len(schedules_to_export)
        n = askinteger("Number of schedules", f"How many? (1-{n_total})", minvalue=1, maxvalue=n_total)
        
        if not n:
            return

        with PdfPages("schedules.pdf") as pdf:
            for i, sched in enumerate(schedules_to_export[:n], start=1):
                percent = (i / n) * 100
                self.status.config(text=f"Exporting: {percent:.1f}% complete...")
                self.root.update_idletasks() # Refresh GUI
                
                fig, ax = plt.subplots(figsize=(12, 8))
                self.plot_schedule(sched, sid=i, ax=ax)
                pdf.savefig(fig)
                plt.close(fig)
                
        self.status.config(text=f"Successfully exported {n} schedules to PDF.")

# ===============================
# Main
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop()

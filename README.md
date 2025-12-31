# Course Schedule Builder

A Python-based GUI application designed to help students automatically generate conflict-free course schedules. It processes a list of available course sections, identifies valid combinations, and provides tools to filter and visualize the results.

---

## 🚀 Features

* **Automatic Generation:** Uses recursive logic to find every possible conflict-free combination of classes.
* **Visual Timetables:** Generates color-coded weekly views using `matplotlib`.
* **Advanced Filtering:**
    * Limit early morning (08:15) or late afternoon classes.
    * Set a maximum number of days on campus.
    * Exclude specific days of the week.
    * Cap the total "gap time" (waiting between classes).
* **PDF Export:** Save schedules to a multi-page PDF document.
* **Optimization:** Sort generated schedules by "Least Gap Time" to minimize time on campus.

---

## 🛠️ Setup & Requirements

1.  **Python 3.10+**
2.  **Dependencies**: Install the required plotting library via your terminal:
    ```bash
    pip install matplotlib
    ```
3.  **Data File**: Ensure a file named `classes.txt` exists in the same directory as the script.

---

## 📝 Data Format (`classes.txt`)

The program reads course data from a text file. Each line represents one section and must follow this underscore-separated format:

`Course_Section_Description_Teacher_Day1_Start1_End1_Day2_Start2_End2...`

### Examples:
* **Standard:** `English_003_Arthurian Legends_Fitz-James_Mon_12:15_14:15_Fri_08:15_10:15`
* **No Description:** `Calculus_001_none_Slavchev_Tue_16:15_17:45_Thu_16:15_17:45`

> **Note:** Use `none` if a description is unavailable. All times must be in **24-hour format (HH:MM)**.

---

## 🖥️ How to Use

1.  **Input Data**: Fill `classes.txt` with your desired courses and sections.
2.  **Run the Script**: Execute the Python file to open the GUI.
3.  **Generate**: Click **Generate Schedules** to find all valid combinations.
4.  **Filter**: Use the checkboxes and spinboxes to narrow down the results (e.g., "Max 2 days on campus").
5.  **Visualize**: Click **Plot Random Schedule** to see a visual layout of a generated option.
6.  **Export**: Use **Export PDF** to save the current filtered results.

---

## ⚠️ Error Handling

If a line in your `classes.txt` is formatted incorrectly, the program will:
1.  Skip the problematic line.
2.  Alert you with a popup window.
3.  Create a `fix_me.txt` file detailing exactly which lines failed and why so you can correct them.

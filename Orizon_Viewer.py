import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, ttk
from tkinter import messagebox
import json
from PIL import Image, ImageTk
import barcode
from barcode.writer import ImageWriter
import io
import os
import sys

def resource_path(relative_path):
    """Vrati pravi path - radi i kad je .exe"""
    try:
        base_path = sys._MEIPASS  # PyInstaller koristi ovo kad raspakira
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ExcelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Orizon Viewer")
        self.geometry("1024x600")
        self.resizable(False, False)
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        self.df = None
        self.column_widths = {}

        self.title_label = ctk.CTkLabel(
            self, text="ORIZON - Viewer", font=("Tenorite", 24, "bold")
        )
        self.title_label.place(x=20, y=10)

        self.logo = Image.open(resource_path("Orizon-com.jpg"))
        self.logo = self.logo.resize((170, 60))
        self.logo_img = ctk.CTkImage(self.logo, size=(170, 60))
        self.logo_label = ctk.CTkLabel(self, image=self.logo_img, text="", cursor="hand2")
        self.logo_label.bind("<Button-1>", self.show_contact_info)
        self.after(100, self.place_logo)

        search_frame = ctk.CTkFrame(self, width=400)  # postavi željenu širinu u pikselima
        search_frame.pack(pady=50, padx=180)


        self.search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Cerca...", font=("Tenorite", 28), width=600, height=50
        )
        self.search_entry.grid(row=0, column=0, pady=15, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.filter_table)

        self.clear_btn = ctk.CTkButton(
            search_frame,
            text="Nuova Ricerca",
            command=self.reset_search,
            font=("Tenorite", 20),
             width=200,     # širina u pikselima
            height=50 
        )
        self.clear_btn.grid(row=0, column=1, padx=5, sticky="ew")

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(pady=10, expand=True, fill="both", padx=20)

        self.scrollbar = ttk.Scrollbar(table_frame, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            table_frame, show="headings", yscrollcommand=self.scrollbar.set
        )
        self.tree.pack(pady=10, expand=True, fill="both", padx=20)
        self.tree.bind("<Double-1>", self.show_popup)

        style = ttk.Style()
        style.configure(
            "Treeview.Heading",
            font=("Tenorite", 24, "bold"),
            background="#1E3D58",
            foreground="white",
        )
        style.configure(
            "Treeview",
            font=("Tenorite", 18),
            rowheight=35,
            foreground="black",
        )
        self.scrollbar.config(command=self.tree.yview)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10, fill="x", padx=20)

        self.import_btn = ctk.CTkButton(
            btn_frame,
            text="Importa Excel",
            command=self.load_excel,
            font=("Tenorite", 20),
            fg_color="green",
            hover_color="darkgreen",
            width=200,    
            height=44
        )
        self.import_btn.pack(side="left", expand=True, padx=5)

        self.exit_btn = ctk.CTkButton(
            btn_frame,
            text="Esci",
            command=self.quit,
            font=("Tenorite", 20),
            fg_color="#8B0000",
            hover_color="#B22222",
            width=200,     # širina u pikselima
            height=44 
        )
        self.exit_btn.pack(side="left", expand=True, padx=5)

        self.load_column_widths()

        # ===> Caricamento automatico del file all'avvio
        default_file = os.path.join(os.getcwd(), "mm16.xlsx")
        if not os.path.exists(default_file):
            default_file = resource_path("mm16.xlsx")  # koristi spakovani fajl ako nema vanjskog


    def place_logo(self):
        x = self.winfo_width() - 174
        self.logo_label.place(x=x, y=3)

    def load_excel(self):
        file_path = filedialog.askopenfilename(
            title="Seleziona un file Excel", filetypes=[("Excel Files", "*.xlsx")]
        )
        if file_path:
            try:
                self.df = pd.read_excel(file_path, sheet_name="Foglio1")
                self.display_data(self.df)
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante l'importazione: {e}")
    
    def show_contact_info(self, event):
        messagebox.showinfo(
        "Orizon Viewer - Info Versione",
        "────── Orizon Viewer ─────\n"
        "Versione: 2.1.1\n"
        "Piattaforma: Windows\n"
        "Linguaggio: Python\n\n"
        "Sviluppatore:\n"
        "Arnel Kovacevic\n"
        "Orizon-AIX\n\n"
        "Copyright © 2025 Orizon-AIX\n"
        "──────────────────────────────────────\n\n"
        "Sito Web: orizon-aix.com\n"
        "Email: info@orizon-aix.com\n"
        "Telefono: +39 380 7525438"
    )


    def display_data(self, df):
        self.tree.delete(*self.tree.get_children())
        selected_columns = [df.columns[0], df.columns[3], df.columns[4], df.columns[5]]

        self.tree["columns"] = selected_columns
        for col in selected_columns:
            self.tree.heading(col, text=col)
            width = self.column_widths.get(col, 150)
            self.tree.column(col, width=width, anchor="center")

        for idx, row in df[selected_columns].iterrows():
            values = list(row)
            row_tags = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=values, tags=(row_tags,))

        self.tree.tag_configure("even", background="#f2f2f2")
        self.tree.tag_configure("odd", background="#ffffff")

    def filter_table(self, event=None):
        text = self.search_entry.get().lower()
        if self.df is not None:
            filtered_df = self.df[
                self.df.astype(str)
                .apply(lambda row: row.str.contains(text, case=False).any(), axis=1)
            ]
            self.display_data(filtered_df)

    def reset_search(self):
        if self.df is not None:
            self.search_entry.delete(0, "end")
            self.display_data(self.df)

    def show_popup(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            item_values = self.tree.item(selected_item, "values")
            if len(item_values) >= 3:
                self.create_popup(item_values)

    def create_popup(self, item_values):
        popup = ctk.CTkToplevel(self)
        popup.geometry("750x500")
        popup.title("Dettagli Articolo")

        spacer = ctk.CTkLabel(popup, text="")
        spacer.pack(pady=70)

        name_label = ctk.CTkLabel(
            popup,
            text=f"{item_values[1]}",
            font=("Tenorite", 28, "bold"),
            text_color="white",
        )
        name_label.pack(pady=20)  # 0 jer ne želimo dodatni razmak ispod

        position_label = ctk.CTkLabel(
            popup,
            text=f"{item_values[3]}",
            font=("Tenorite", 40, "bold"),
            text_color="green",
        )
        position_label.pack(pady=20)

        barcode_data = str(item_values[0])
        barcode_image = self.generate_barcode(barcode_data)
        if barcode_image:
            barcode_label = ctk.CTkLabel(popup, image=barcode_image, text="")
            barcode_label.image = barcode_image
            barcode_label.pack(pady=20)

        close_btn = ctk.CTkButton(
            popup, text="Chiudi", command=popup.destroy, font=("Tenorite", 24),
            width=200,     # širina u pikselima
            height=52
        )
        close_btn.pack(pady=30)

    def generate_barcode(self, data):
        try:
            barcode_class = barcode.get_barcode_class("code128")
            barcode_obj = barcode_class(data, writer=ImageWriter())
            buffer = io.BytesIO()
            barcode_obj.write(
                buffer, options={"module_height": 18.0, "font_size": 10, "quiet_zone": 2}
            )
            buffer.seek(0)
            pil_image = Image.open(buffer)
            pil_image = pil_image.resize((400, 120))
            barcode_img = ImageTk.PhotoImage(pil_image)
            return barcode_img
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel generare il codice a barre: {e}")
            return None

    def load_column_widths(self):
        try:
            with open("column_widths.json", "r") as f:
                self.column_widths = json.load(f)
        except FileNotFoundError:
            self.column_widths = {}


if __name__ == "__main__":
    app = ExcelApp()
    app.mainloop()

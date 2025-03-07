# app/menu.py
import tkinter as tk
from app.screens.map_screen import show_map
from app.screens.about_screen import show_about
from app.screens.ap_registration import show_ap_registration

def create_menu(root):
    menu_bar = tk.Menu(root)

    # Menu "Arquivo"
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Registro", command=lambda: show_ap_registration(root))
    file_menu.add_command(label="Mapa", command=lambda: show_map(root))
    file_menu.add_separator()
    file_menu.add_command(label="Sair", command=root.quit)
    menu_bar.add_cascade(label="Arquivo", menu=file_menu)

    # Menu "Ajuda"
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="Sobre", command=lambda: show_about(root))
    menu_bar.add_cascade(label="Ajuda", menu=help_menu)

    root.config(menu=menu_bar)

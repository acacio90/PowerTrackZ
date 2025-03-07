import tkinter as tk
from app.events import show_home, show_about, exit_app

def create_menu(root):
    menu_bar = tk.Menu(root)

    # Menu "Arquivo"
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Home", command=show_home)
    file_menu.add_separator()
    file_menu.add_command(label="Sair", command=exit_app)
    menu_bar.add_cascade(label="Arquivo", menu=file_menu)

    # Menu "Ajuda"
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="Sobre", command=lambda: show_about(root))
    menu_bar.add_cascade(label="Ajuda", menu=help_menu)

    # Adiciona a barra de menu à janela principal
    root.config(menu=menu_bar)

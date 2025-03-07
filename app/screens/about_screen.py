# app/screens/about_screen.py
import tkinter as tk
from tkinter import ttk

def show_about(root):
    """Exibe a tela de Informações sobre o aplicativo"""
    about_window = tk.Toplevel(root)
    about_window.title("Sobre")
    about_window.geometry("400x300")
    about_window.resizable(False, False)

    frame = ttk.Frame(about_window, padding="10")
    frame.pack(fill="both", expand=True)

    title_label = ttk.Label(frame, text="Sobre o Aplicativo", font=('Arial', 16, 'bold'))
    title_label.pack(pady=10)

    description_label = ttk.Label(frame, text=""
    "Desenvolvido por Pedro Acácio Rodrigues\n"
    "Graduando em Ciência da Computação pela Universidade Técnilogica Federal do Paraná (UTFPR)-CM\n"
    "GitHub: https://github.com/acacio90\n"
    "\nEste aplicativo foi criado para fornecer insights da melhor configuração para pontos de acesso em determinado ambiente.", font=('Arial', 12), wraplength=380, justify="center")
    description_label.pack(pady=10)

    version_label = ttk.Label(frame, text="Versão 1.0.0", font=('Arial', 10, 'italic'))
    version_label.pack(pady=10)

    close_button = ttk.Button(frame, text="Fechar", command=about_window.destroy)
    close_button.pack(pady=20)
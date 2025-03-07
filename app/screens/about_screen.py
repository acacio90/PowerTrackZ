# app/screens/about_screen.py
import tkinter as tk

def show_about(root):
    """Exibe a tela de Informações sobre o aplicativo"""
    about_window = tk.Toplevel(root)
    about_window.title("Sobre")
    about_window.geometry("400x300")

    about_label = tk.Label(about_window, text="App", font=('Arial', 14))
    about_label.pack(pady=20)

    close_button = tk.Button(about_window, text="Fechar", command=about_window.destroy)
    close_button.pack(pady=10)

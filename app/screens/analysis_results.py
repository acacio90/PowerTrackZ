# app/screens/analysis_results.py
import tkinter as tk
from tkinter import ttk

def show_analysis_results(root, results):
    """Exibe os resultados da análise"""
    results_window = tk.Toplevel(root)
    results_window.title("Resultados da Análise")
    results_window.geometry("600x400")
    results_window.resizable(False, False)

    frame = ttk.Frame(results_window, padding="10")
    frame.pack(fill="both", expand=True)

    columns = ("Ponto A", "Ponto B", "Problema", "Solução")
    tree = ttk.Treeview(frame, columns=columns, show="headings")

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150)

    for result in results:
        tree.insert("", "end", values=result)

    tree.pack(fill="both", expand=True)

    close_button = ttk.Button(frame, text="Fechar", command=results_window.destroy)
    close_button.pack(pady=10)
# app/screens/ap_registration.py
import tkinter as tk
from tkinter import ttk, Button, Label
import csv

def show_ap_registration(root, main_window):
    """Exibe a tela de cadastro de pontos de acesso"""
    registration_window = tk.Toplevel(root)
    registration_window.title("Cadastro de Ponto de Acesso")
    registration_window.geometry("600x400")

    description_label = Label(registration_window, text="Descrição do Ponto de Acesso:")
    description_label.pack(pady=5)
    description_entry = ttk.Entry(registration_window)
    description_entry.pack(pady=5)

    latitude_label = Label(registration_window, text="Latitude:")
    latitude_label.pack(pady=5)
    latitude_entry = ttk.Entry(registration_window)
    latitude_entry.pack(pady=5)

    longitude_label = Label(registration_window, text="Longitude:")
    longitude_label.pack(pady=5)
    longitude_entry = ttk.Entry(registration_window)
    longitude_entry.pack(pady=5)

    def add_ap():
        description = description_entry.get()
        latitude = latitude_entry.get()
        longitude = longitude_entry.get()
        
        if description and latitude and longitude:
            tree.insert("", "end", values=(description, latitude, longitude))
            
            # Salvar no arquivo CSV
            filename = "pontos_de_acesso.csv"
            with open(filename, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([description, latitude, longitude])
            
            # Limpar os campos
            description_entry.delete(0, "end")
            latitude_entry.delete(0, "end")
            longitude_entry.delete(0, "end")
            error_label.config(text="")
        
            # Atualizar tabela principal
            main_window.load_data()
        else:
            error_label.config(text="Por favor, preencha todos os campos.")

    add_button = Button(registration_window, text="Adicionar Ponto de Acesso", command=add_ap)
    add_button.pack(pady=10)

    columns = ("Descrição", "Latitude", "Longitude")
    tree = ttk.Treeview(registration_window, columns=columns, show="headings", height=5)
    
    tree.heading("Descrição", text="Descrição")
    tree.heading("Latitude", text="Latitude")
    tree.heading("Longitude", text="Longitude")
    
    tree.pack(pady=20, fill="x", expand=False)

    error_label = Label(registration_window, text="", fg="red")
    error_label.pack(pady=5)
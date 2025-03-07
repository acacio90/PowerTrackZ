# app/main_window.py
import tkinter as tk
from tkinter import ttk
import csv
from app.menu import create_menu
from app.zabbix_api import ZabbixConnector
from app.screens.ap_registration import show_ap_registration


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("App de Gastos Energéticos")
        self.root.state('zoomed')

        # Conectar ao Zabbix
        self.zabbix = ZabbixConnector("config.ini", verify=False)

        # Limpar a janela
        for widget in self.root.winfo_children():
            widget.destroy()

        # Menu
        create_menu(self.root)

        home_label = tk.Label(self.root, text="Tela Inicial", font=('Arial', 24))
        home_label.pack(pady=20)

        register_button = tk.Button(self.root, text="Cadastrar Ponto de Acesso", command=self.open_registration_window)
        register_button.pack(pady=10)

        self.load_data()

    def load_data(self):
        """Carrega os dados dos pontos de acesso e os exibe na tabela"""
        filename = "pontos_de_acesso.csv"
        
        if hasattr(self, 'tree'):
            self.reload_data()
        else:
            # Criação da tabela
            columns = ("Descrição", "Latitude", "Longitude")
            self.tree = ttk.Treeview(self.root, columns=columns, show="headings")

            self.tree.heading("Descrição", text="Descrição")
            self.tree.heading("Latitude", text="Latitude")
            self.tree.heading("Longitude", text="Longitude")

            self.tree.pack(pady=20, fill="both", expand=True)

            self.reload_data()

            delete_button = tk.Button(self.root, text="Excluir Ponto de Acesso", command=self.delete_record)
            delete_button.pack(pady=10)

    def reload_data(self):
        """Recarrega os dados dos pontos de acesso na tabela"""
        filename = "pontos_de_acesso.csv"
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            with open(filename, mode="r") as file:
                reader = csv.reader(file)
                try:
                    next(reader)  # Ignorar cabeçalho
                except StopIteration:
                    print("Arquivo CSV está vazio.")
                    return
                for row in reader:
                    self.tree.insert("", "end", values=row)
        except FileNotFoundError:
            print("Arquivo de dados não encontrado.")

    def delete_record(self):
        """Excluir o registro selecionado na tabela e no arquivo CSV"""
        selected_item = self.tree.selection()
        
        if selected_item:
            values = self.tree.item(selected_item)["values"]
            
            self.tree.delete(selected_item)
            
            # Ler os dados do arquivo CSV
            filename = "pontos_de_acesso.csv"
            data = []
            with open(filename, mode="r") as file:
                reader = csv.reader(file)
                header = next(reader)
                for row in reader:
                    data.append(row)
            
            # Filtrar o registro selecionado (não o incluir)
            data = [row for row in data if row != values]
            
            # Reescrever os dados no arquivo CSV sem o registro excluído
            with open(filename, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(header)  # Escrever cabeçalho
                writer.writerows(data)  # Escrever os dados restantes

            print(f"Ponto de Acesso {values[0]} excluído.")
            
            # Recarregar os dados na tabela
            self.reload_data()
        else:
            print("Nenhum ponto de acesso selecionado.")

    def open_registration_window(self):
        """Abre a janela de cadastro de pontos de acesso"""
        show_ap_registration(self.root, self)

    def run(self):
        """Inicia o loop principal da interface gráfica"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()